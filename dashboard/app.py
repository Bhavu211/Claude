"""Career Copilot Dashboard — New Analysis (home page).

Upload a resume + JD, enter company/role, run the real 18-agent pipeline,
and watch it execute live. Every other sidebar page reads from the same
SQLite database this page writes to.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from career_copilot.core.demo_client import DemoLLMClient
from career_copilot.pipeline import ExecutionEvent, PipelineInput, run_pipeline
from career_copilot.core.run_log import RunLogger
from dashboard import db
from dashboard.components.activity_console import render_console
from dashboard.components.cards import render_summary_cards
from dashboard.components.execution_graph import STATUS_COLORS, build_execution_graph_figure
from dashboard.discovery import discover_agents
from dashboard.file_parsing import UnsupportedFileType, extract_text
from dashboard.output_manager import create_output_folder, save_application_outputs

st.set_page_config(page_title="Career Copilot", page_icon="🧭", layout="wide")

CSS = """
<style>
:root { --cc-border: #E4E4E7; --cc-muted: #6B7280; }
[data-testid="stMetric"] { background: var(--background-color, #fff); border: 1px solid var(--cc-border);
    border-radius: 10px; padding: 12px 16px; }
.cc-agent-card { border: 1px solid var(--cc-border); border-radius: 10px; padding: 10px 14px; margin-bottom: 6px; }
.cc-badge { display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
h1, h2, h3 { font-weight: 650; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

db.init_db()

st.title("🧭 Career Copilot")
st.caption("Resume optimization, ATS analysis, company research, and interview prep — orchestrated by 18 verified AI agents.")

render_summary_cards()
st.divider()

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

st.header("New Analysis")

agents = discover_agents()
specialist_agents = [a for a in agents if a.category != "orchestration"]

col_left, col_right = st.columns(2)

with col_left:
    resume_file = st.file_uploader("Resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])
    jd_mode = st.radio("Job Description input", ["Upload file", "Paste text"], horizontal=True)
    jd_file = None
    jd_pasted = ""
    if jd_mode == "Upload file":
        jd_file = st.file_uploader("Job Description (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"], key="jd_upload")
    else:
        jd_pasted = st.text_area("Paste job description text", height=180)

with col_right:
    candidate_name = st.text_input("Candidate name", value="")
    company_name = st.text_input("Company name")
    job_title = st.text_input("Job title")
    years_of_experience = st.text_input("Years of experience (optional)")
    user_goal = st.text_area(
        "What do you want from this run?", height=90,
        value="I want a tailored resume, a gap analysis, and interview prep.",
    )

has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
live_passcode = os.environ.get("LIVE_MODE_PASSCODE")  # optional — unset means Live mode is ungated
mode = st.radio(
    "Execution mode",
    ["Demo (replays verified sample outputs, no API key needed)", "Live (calls the real Anthropic API)"],
    index=0 if not has_key else 1,
    horizontal=True,
)
if mode.startswith("Live") and not has_key:
    st.warning("ANTHROPIC_API_KEY is not set in this environment — live mode will fail. Set it or use Demo mode.")

passcode_ok = True
entered_passcode = ""
if mode.startswith("Live") and live_passcode:
    entered_passcode = st.text_input("Live mode passcode", type="password", help="This deployment restricts Live mode (billed API calls) to people who know the passcode.")
    passcode_ok = hmac.compare_digest(entered_passcode, live_passcode)
    if entered_passcode and not passcode_ok:
        st.error("Incorrect passcode — Live mode stays locked. Use Demo mode instead, or get the correct passcode.")

# Preview uploaded files
if resume_file or jd_file:
    with st.expander("Uploaded files", expanded=True):
        if resume_file:
            st.write(f"📄 **{resume_file.name}** — {resume_file.size:,} bytes")
        if jd_file:
            st.write(f"📄 **{jd_file.name}** — {jd_file.size:,} bytes")

run_clicked = st.button(
    "▶ Run Pipeline", type="primary",
    disabled=not (resume_file and (jd_file or jd_pasted) and company_name and job_title and passcode_ok),
)

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

if run_clicked:
    if mode.startswith("Live") and live_passcode and not passcode_ok:
        st.error("Live mode is locked behind a passcode on this deployment.")
        st.stop()

    try:
        resume_text = extract_text(resume_file.name, resume_file.getvalue())
    except UnsupportedFileType as exc:
        st.error(str(exc))
        st.stop()

    if jd_file:
        try:
            jd_text = extract_text(jd_file.name, jd_file.getvalue())
        except UnsupportedFileType as exc:
            st.error(str(exc))
            st.stop()
    else:
        jd_text = jd_pasted

    pipeline_input = PipelineInput(
        candidate_name=candidate_name or "Candidate",
        target_role=job_title,
        resume_text=resume_text,
        jd_text=jd_text or None,
        company_name=company_name or None,
        user_goal=user_goal,
    )

    application_id = db.create_application(
        candidate_name=pipeline_input.candidate_name, company_name=company_name,
        job_title=job_title, years_of_experience=years_of_experience or None,
    )

    st.subheader("Live Execution Monitor")
    progress_bar = st.progress(0.0)
    progress_caption = st.empty()
    graph_placeholder = st.empty()
    st.subheader("Live Activity Console")
    console_placeholder = st.empty()

    statuses = {a.id: "pending" for a in specialist_agents}
    log_rows = []
    started_at = {}
    run_started = time.monotonic()
    planned_order = {"ids": []}
    render_count = {"n": 0}

    def render_live(running_agent_id=None):
        render_count["n"] += 1
        planned = planned_order["ids"] or [a.id for a in specialist_agents]
        graph_agents = [a for a in specialist_agents if a.id in planned] or specialist_agents
        fig = build_execution_graph_figure(graph_agents, statuses, running_agent_id=running_agent_id)
        graph_placeholder.plotly_chart(fig, use_container_width=True, key=f"graph_{render_count['n']}")
        console_placeholder.empty()
        with console_placeholder.container():
            render_console(log_rows, key_prefix=f"live_{render_count['n']}")

        total = len(planned) if planned else 1
        done = sum(1 for aid in planned if statuses.get(aid) in ("completed", "failed"))
        pct = done / total
        progress_bar.progress(pct)
        elapsed = time.monotonic() - run_started
        eta = (elapsed / done * (total - done)) if done else None
        eta_str = f"~{eta:.0f}s remaining" if eta is not None else "estimating…"
        progress_caption.caption(f"{done}/{total} agents complete ({pct*100:.0f}%) · {elapsed:.1f}s elapsed · {eta_str}")

    def on_event(event: ExecutionEvent) -> None:
        if event.event_type == "plan_ready":
            planned_order["ids"] = [aid for aid in (event.run_order or []) if aid in statuses]
            for aid in list(statuses):
                if aid not in planned_order["ids"]:
                    statuses[aid] = "skipped"
        elif event.event_type == "agent_started":
            statuses[event.agent_id] = "running"
            started_at[event.agent_id] = time.monotonic()
        elif event.event_type == "agent_completed":
            statuses[event.agent_id] = "completed"
        elif event.event_type == "agent_failed":
            statuses[event.agent_id] = "failed"

        if event.agent_id and event.event_type in ("agent_started", "agent_completed", "agent_failed"):
            elapsed_ms = None
            if event.event_type != "agent_started" and event.agent_id in started_at:
                elapsed_ms = int((time.monotonic() - started_at[event.agent_id]) * 1000)
            log_rows.append({
                "timestamp": event.timestamp, "agent": event.agent_id,
                "task": event.message, "status": event.event_type.replace("agent_", ""),
                "duration_ms": elapsed_ms, "error": event.error or "",
            })
            db.insert_execution_log(
                application_id, event.agent_id, event.event_type.replace("agent_", ""),
                task=event.message, duration_ms=elapsed_ms, error=event.error,
            )
        elif event.event_type in ("critic_started", "critic_completed", "supervisor_started", "supervisor_completed"):
            log_rows.append({
                "timestamp": event.timestamp, "agent": event.event_type.split("_")[0],
                "task": event.message, "status": "running" if "started" in event.event_type else "completed",
                "duration_ms": None, "error": "",
            })

        render_live(running_agent_id=event.agent_id if event.event_type == "agent_started" else None)

    render_live()

    client_factory = (lambda: DemoLLMClient(delay_seconds=0.15)) if mode.startswith("Demo") else None
    logger = RunLogger(db_path="career_copilot_runs.sqlite3")

    with st.spinner("Running..."):
        try:
            result = run_pipeline(pipeline_input, logger=logger, on_event=on_event, client_factory=client_factory)
        except Exception as exc:  # noqa: BLE001 — surface the real error in the UI rather than a raw traceback
            db.complete_application(
                application_id, ats_score=None, skills_missing=[], interview_readiness=None,
                quality_gate=None, status="failed", output_folder=None,
            )
            st.error(f"Pipeline run failed: {exc}")
            st.stop()

    resume_version_hash = hashlib.sha256(resume_text.encode("utf-8")).hexdigest()[:12]
    ats_out = result.agent_outputs.get("ats_optimization")
    gap_out = result.agent_outputs.get("gap_analysis")
    skill_out = result.agent_outputs.get("skill_evidence")
    skills_missing = []
    if gap_out:
        skills_missing.extend(gap_out.get("critical_gaps", []))
    if skill_out:
        skills_missing.extend(s for s in skill_out.get("weakly_evidenced_skills", []) if s not in skills_missing)

    folder = create_output_folder(company_name, job_title)
    written = save_application_outputs(
        folder, result, original_resume_text=resume_text, original_jd_text=jd_text or None,
        metadata={
            "candidate_name": pipeline_input.candidate_name, "company_name": company_name,
            "job_title": job_title, "mode": mode, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    resume_version_id = db.insert_resume_version(
        label=f"{company_name} / {job_title}", content_hash=resume_version_hash,
        ats_score=ats_out.get("ats_compatibility_score") if ats_out else None,
        application_id=application_id,
    )

    interview_readiness = None
    if result.supervisor_output:
        interview_readiness = "ready" if result.supervisor_output.final_deliverable_ready else "not_ready"

    db.complete_application(
        application_id, ats_score=ats_out.get("ats_compatibility_score") if ats_out else None,
        skills_missing=skills_missing, interview_readiness=interview_readiness,
        quality_gate=result.supervisor_output.quality_gate.value if result.supervisor_output else None,
        status="completed", output_folder=str(folder),
    )

    company_intel = result.agent_outputs.get("company_intelligence")
    if company_intel:
        db.update_company_research(
            company_name, industry=company_intel.get("industry"),
            products=[p.get("name", str(p)) for p in company_intel.get("products", [])] if company_intel.get("products") else None,
            tech_stack=company_intel.get("tech_stack"), culture=company_intel.get("engineering_culture"),
            recent_news=[n.get("headline", str(n)) for n in company_intel.get("recent_news", [])] if company_intel.get("recent_news") else None,
            required_skills=None,
        )

    st.success(f"Pipeline complete — output saved to `{folder}`")
    gate = result.supervisor_output.quality_gate.value if result.supervisor_output else "unknown"
    ready = result.supervisor_output.final_deliverable_ready if result.supervisor_output else False
    badge_color = "#16A34A" if ready else "#D97706"
    st.markdown(
        f"<span class='cc-badge' style='background:{badge_color}20;color:{badge_color};'>"
        f"Quality gate: {gate} · {'Ready to deliver' if ready else 'Needs attention'}</span>",
        unsafe_allow_html=True,
    )
    if ats_out:
        st.metric("ATS Score", ats_out.get("ats_compatibility_score"))

    st.write("**Artifacts saved:**")
    for name, path in written.items():
        st.write(f"- `{name}` → `{path}`")
    st.info("See the **Outputs** page to preview/download individual artifacts, or **Previous Applications** for this run's summary.")
