# Roadmap — AI Career Copilot

## v0.1 — Done (this repo, current state)

- All 18 agents built, each with a validated Pydantic schema and a hand-verified sample output.
- `pipeline.py`: real end-to-end orchestration, dependency-ordered, wired from actual upstream structured fields (not re-passed text).
- Non-fabrication discipline enforced structurally across every agent (explicit null/insufficient-evidence handling, `AGENT_REGISTRY`-grounded orchestration).
- Per-agent documentation (`docs/agents/`), product docs (`docs/product/`), and portfolio materials (`docs/portfolio/`).

## v0.2 — Next: make it runnable and measurable

- **Live validation (Phase 1):** run each agent against 10-20 varied real inputs (easy/normal/edge/bad-input/missing-info) once an `ANTHROPIC_API_KEY` is available; fix prompts against real failure modes, not just the one hand-built sample per agent.
- **Run persistence (Phase 5 — scaffolded in this repo):** every `run_pipeline()` call logged to SQLite (date, company, JD, resume version, ATS score, skills missing, interview questions) so runs accumulate into real, queryable history instead of being thrown away.
- **Evaluation harness (Phase 7 — scaffolded in this repo):** LLM-as-judge scoring plus token/cost tracking per run, so "this agent works" becomes a measured accuracy/completeness/hallucination-rate/cost number, not an assertion.
- **A real UI:** a Streamlit front end over `pipeline.py` so a non-technical user can actually run this without writing Python.

## v0.3 — Automate and harden

- Workflow automation (upload resume/JD → full pipeline → notify user when ready) via n8n or an equivalent orchestration layer, using the already-built `pipeline.py` as the core logic.
- Multiple recruiter/interviewer personas in Recruiter Simulation and Interview Coach, instead of one fixed voice.
- Partial re-runs: Supervisor Agent can already flag exactly which agents need revision; v0.3 should let the pipeline re-invoke only those agents instead of a full re-run.
- Cost controls: per-run budget caps, and Planner-driven agent selection that respects a stated budget, not just a stated intent.

## v0.4 — Product-ize

- Decide and validate a pricing/access model (see `docs/product/PRD.md` open questions).
- User accounts and history across sessions (currently every run is stateless beyond the local SQLite log).
- Outcome tracking: correlate system usage with actual interview/offer outcomes, once there's a real user base — this is the metric that actually matters and can only be measured with real usage over time.

## Explicitly deferred / not planned

- Auto-submitting applications or auto-sending outreach on the user's behalf — the system drafts, the user sends. This is a deliberate scope boundary (see PRD non-goals), not a backlog item.
- Resume design/typesetting (PDF layout) — out of scope; this system produces content, not document design.
