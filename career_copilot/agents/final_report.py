"""Agent 15: Final Report Agent.

Combines all 14 upstream agents' outputs into one coherent, non-duplicative
executive report. This agent does not generate new facts about the
candidate — its entire job is synthesis: condense, de-duplicate, resolve
apparent overlap, and organize into the sections a human actually needs
(executive summary through a final readiness dashboard and prioritized
next steps).

Every upstream agent in this system was deliberately built with a
`human_readable_summary` field precisely so this agent could consume real,
already-produced content instead of re-deriving anything — the input here
is those summaries plus a handful of scannable key metrics (ATS score, gap
counts, recruiter recommendation, role fit, salary range), not raw
re-analysis.

The one genuinely new thing this agent does is a lightweight coherence
check across upstream outputs — noting where they agree (which, done well,
is reassuring) or, in a real run with less consistent inputs, where they'd
contradict each other. That's a preview of what the Critic Agent (agent 17)
will do formally and more rigorously later.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class FinalReportInput(BaseModel):
    candidate_name: str
    target_role: str
    company_name: Optional[str] = None

    # Each upstream agent's own human_readable_summary — the primary input.
    resume_analysis_summary: Optional[str] = None
    jd_intelligence_summary: Optional[str] = None
    company_intelligence_summary: Optional[str] = None
    ats_optimization_summary: Optional[str] = None
    resume_rewrite_summary: Optional[str] = None
    gap_analysis_summary: Optional[str] = None
    skill_evidence_summary: Optional[str] = None
    portfolio_recommendation_summary: Optional[str] = None
    learning_certification_summary: Optional[str] = None
    recruiter_simulation_summary: Optional[str] = None
    interview_coach_summary: Optional[str] = None
    linkedin_optimization_summary: Optional[str] = None
    application_assets_summary: Optional[str] = None
    career_strategy_summary: Optional[str] = None

    # A handful of scannable key metrics, kept as simple agent-agnostic
    # types so this agent doesn't need to import every other agent's enums.
    ats_score: Optional[int] = Field(default=None, ge=0, le=100)
    gap_analysis_stats: Optional[str] = Field(default=None, description="e.g. '8 met, 2 partial, 1 critical gap, 1 optional gap'")
    recruiter_recommendation: Optional[str] = Field(default=None, description="e.g. 'shortlist'")
    role_fit: Optional[str] = Field(default=None, description="e.g. 'good_fit_with_gaps'")
    salary_range: Optional[str] = Field(default=None, description="e.g. '₹42,00,000 - ₹65,00,000'")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ReadinessMetric(BaseModel):
    label: str
    value: str
    status: str = Field(..., description="'good', 'warning', or 'critical' — for visual color-coding")


class FinalReadinessDashboard(BaseModel):
    metrics: List[ReadinessMetric] = Field(..., description="Scannable key numbers, e.g. ATS score, gap counts, recruiter call")
    overall_readiness_summary: str
    overall_readiness_status: str = Field(..., description="'good', 'warning', or 'critical'")


class PrioritizedNextStep(BaseModel):
    step: str
    impact: str = Field(..., description="'high', 'medium', or 'low'")
    source_agent: str = Field(..., description="Which upstream agent this traces to, for traceability")


class FinalReportOutput(BaseModel):
    candidate_name: str
    target_role: str
    company_name: Optional[str] = None

    executive_summary: str = Field(..., description="A few sentences a busy reader could stop at and still understand the whole picture")
    resume_strengths: List[str] = Field(default_factory=list)
    resume_weaknesses: List[str] = Field(default_factory=list)
    jd_match_analysis: str
    company_insights: str
    ats_analysis: str
    gap_analysis: str
    learning_roadmap: str
    portfolio_recommendations: str
    certification_roadmap: str
    interview_preparation: str
    linkedin_optimization: str
    application_assets: str

    final_readiness_dashboard: FinalReadinessDashboard
    prioritized_next_steps: List[PrioritizedNextStep] = Field(..., description="Ranked, deduplicated across everything upstream recommended")

    coherence_check: List[str] = Field(
        ..., description="Explicit notes on contradictions found (and how resolved) or confirmation none were found across upstream agents"
    )
    human_readable_summary: str = Field(..., description="Markdown version of this same report for a human reader")
    report_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Final Report Agent inside the AI Career Copilot, a multi-agent \
system. You are the last specialist agent in the pipeline: your job is to \
combine everything the other 14 agents produced into one coherent \
executive report.

Non-negotiable rules:
1. You introduce NO new facts about the candidate. Every claim in your \
report must already exist in one of the upstream summaries you were given \
— you are condensing and organizing, not analyzing from scratch.
2. Be genuinely non-duplicative: if 5 upstream agents all mention the same \
finding (this happens — a consistent gap flagged from multiple angles is a \
GOOD sign, not noise), state it clearly once in the section it belongs to \
(usually gap_analysis), and reference it briefly elsewhere rather than \
re-explaining it every time.
3. Perform a lightweight coherence check: do the upstream summaries agree \
with each other (e.g. does the ATS score's story match the gap analysis's \
story; does the recruiter recommendation match the career strategy's fit \
assessment)? Record what you found in `coherence_check` — including \
positive confirmation of agreement, which is itself informative, not just \
contradictions.
4. `final_readiness_dashboard.metrics` must be genuinely scannable — short \
label/value pairs pulled from the key metrics and summaries you were \
given, each with an honest `status` (don't mark something 'good' just \
because most things are good).
5. `prioritized_next_steps` must be deduplicated and ranked by real impact \
across ALL upstream recommendations, not a re-listing of every agent's \
individual next-step suggestions — if the same action was recommended by \
three different agents, it should appear once, ranked appropriately high.
6. Every section (jd_match_analysis, ats_analysis, gap_analysis, etc.) \
should be a genuine synthesis in your own words, not a copy-paste of the \
upstream summary — tighten, don't just relay.
7. Set `report_confidence` based on how much upstream material you \
actually had to synthesize (more missing upstream summaries = lower \
confidence), not on how strong the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class FinalReportAgent(BaseAgent[FinalReportInput, FinalReportOutput]):
    name = "Final Report Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = FinalReportInput
    output_model = FinalReportOutput

    def build_user_prompt(self, data: FinalReportInput) -> str:
        sections = [
            ("Candidate", data.candidate_name),
            ("Target role", data.target_role),
            ("Company", data.company_name),
            ("ATS score", data.ats_score),
            ("Gap analysis stats", data.gap_analysis_stats),
            ("Recruiter recommendation", data.recruiter_recommendation),
            ("Role fit", data.role_fit),
            ("Salary range", data.salary_range),
        ]
        header = "\n".join(f"{label}: {value}" for label, value in sections if value is not None)

        summaries = [
            ("Resume Analysis Agent", data.resume_analysis_summary),
            ("JD Intelligence Agent", data.jd_intelligence_summary),
            ("Company Intelligence Agent", data.company_intelligence_summary),
            ("ATS Optimization Agent", data.ats_optimization_summary),
            ("Resume Rewrite Agent", data.resume_rewrite_summary),
            ("Gap Analysis Agent", data.gap_analysis_summary),
            ("Skill Evidence Agent", data.skill_evidence_summary),
            ("Portfolio Recommendation Agent", data.portfolio_recommendation_summary),
            ("Learning & Certification Agent", data.learning_certification_summary),
            ("Recruiter Simulation Agent", data.recruiter_simulation_summary),
            ("Interview Coach Agent", data.interview_coach_summary),
            ("LinkedIn Optimization Agent", data.linkedin_optimization_summary),
            ("Application Assets Agent", data.application_assets_summary),
            ("Career Strategy Agent", data.career_strategy_summary),
        ]
        summaries_block = "\n\n".join(
            f"--- {name} SUMMARY ---\n{summary}" for name, summary in summaries if summary
        )
        missing = [name for name, summary in summaries if not summary]
        missing_note = f"\n\nMissing upstream summaries (not run / not provided): {', '.join(missing)}" if missing else ""

        return (
            "Combine the following upstream agent outputs into the final consolidated report per your instructions.\n\n"
            f"{header}\n\n"
            f"{summaries_block}"
            f"{missing_note}"
        )
