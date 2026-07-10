# Career Copilot

A multi-agent AI system that turns a resume + job description + company into a
truthful, evidence-based job application package: gap analysis, ATS-optimized
resume rewrites, interview prep, LinkedIn optimization, and a final recruiter-style
report — built from 18 specialized agents orchestrated by a Planner/Supervisor/Critic
layer.

Every agent follows the same contract: **structured JSON in, structured JSON out,
never fabricate.** Agents are built and verified one at a time.

## Status

| # | Agent | Status |
|---|-------|--------|
| 1 | Resume Analysis Agent | ✅ Built, sample-verified |
| 2 | JD Intelligence Agent | ✅ Built, sample-verified |
| 3 | Company Intelligence Agent | ✅ Built, sample-verified |
| 4 | ATS Optimization Agent | ✅ Built, sample-verified |
| 5 | Resume Rewrite Agent | ✅ Built, sample-verified |
| 6 | Gap Analysis Agent | ✅ Built, sample-verified |
| 7 | Skill Evidence Agent | ✅ Built, sample-verified |
| 8 | Portfolio Recommendation Agent | ✅ Built, sample-verified |
| 9 | Learning & Certification Agent | ✅ Built, sample-verified |
| 10 | Recruiter Simulation Agent | ✅ Built, sample-verified |
| 11 | Interview Coach Agent | ✅ Built, sample-verified |
| 12 | LinkedIn Optimization Agent | ✅ Built, sample-verified |
| 13 | Application Assets Agent | ✅ Built, sample-verified |
| 14 | Career Strategy Agent | ✅ Built, sample-verified |
| 15 | Final Report Agent | ✅ Built, sample-verified |
| 16 | Planner Agent | ✅ Built, sample-verified |
| 17 | Critic Agent | ⏳ Not started |
| 18 | Supervisor Agent | ⏳ Not started |

## Architecture

```
career_copilot/
  core/
    common.py        # shared enums/types (ConfidenceLevel, Severity, QualityIssue, ...)
    llm_client.py     # Anthropic API wrapper — forces structured JSON via tool_choice;
                       # also run_with_web_search() for research-grounded agents
    base_agent.py     # BaseAgent[TIn, TOut]: validated input -> validated output
    registry.py        # AGENT_REGISTRY — machine-readable catalog of all 15 specialist
                         # agents (requires/optional_inputs/depends_on) that Planner and
                         # Supervisor ground their orchestration in, instead of guessing
  agents/
    resume_analysis.py       # Agent 1
    jd_intelligence.py       # Agent 2
    company_intelligence.py  # Agent 3 — two-phase: web research, then structure
    ats_optimization.py      # Agent 4
    resume_rewrite.py        # Agent 5
    gap_analysis.py           # Agent 6
    skill_evidence.py         # Agent 7
    portfolio_recommendation.py  # Agent 8 — takes structured gaps, not a raw document
    learning_certification.py    # Agent 9 — two-phase like Company Intelligence
    recruiter_simulation.py      # Agent 10
    interview_coach.py           # Agent 11
    linkedin_optimization.py     # Agent 12
    application_assets.py        # Agent 13
    career_strategy.py           # Agent 14 — two-phase like Company Intelligence; synthesizes agents 6-10
    final_report.py               # Agent 15 — synthesizes all 14 upstream agents' summaries
    planner.py                     # Agent 16 — orchestration layer; plans against AGENT_REGISTRY
  cli.py              # run a single agent from the command line (docs-only agents)
samples/
  sample_resume.txt   # fixture used to verify agents 1, 4, 5, 6, 7, 10, 11, 12, 13, 14
  sample_jd.txt        # fixture used to verify agents 2, 4, 5, 6, 7, 10, 11, 12, 13 (paired with sample_resume.txt's PM/fintech profile)
outputs/
  resume_analysis_sample_output.{json,md}     # verified sample output, agent 1
  jd_intelligence_sample_output.{json,md}      # verified sample output, agent 2
  company_intelligence_sample_output.{json,md} # verified sample output, agent 3
  ats_optimization_sample_output.{json,md}     # verified sample output, agent 4
  resume_rewrite_sample_output.{json,md}       # verified sample output, agent 5
  gap_analysis_sample_output.{json,md}         # verified sample output, agent 6
  skill_evidence_sample_output.{json,md}       # verified sample output, agent 7
  portfolio_recommendation_sample_output.{json,md} # verified sample output, agent 8
  learning_certification_sample_output.{json,md}   # verified sample output, agent 9
  recruiter_simulation_sample_output.{json,md}     # verified sample output, agent 10
  interview_coach_sample_output.{json,md}          # verified sample output, agent 11
  linkedin_optimization_sample_output.{json,md}    # verified sample output, agent 12
  application_assets_sample_output.{json,md}       # verified sample output, agent 13
  career_strategy_sample_output.{json,md}          # verified sample output, agent 14
  final_report_sample_output.{json,md}             # verified sample output, agent 15 — the consolidated dashboard
  planner_sample_output.{json,md}                  # verified sample output, agent 16
```

Every agent:
- Declares a Pydantic `input_model` and `output_model` (the output model's JSON
  schema doubles as the Anthropic tool schema, so the model is forced to return
  valid, typed JSON — not free text to parse).
- Has a `system_prompt` written from the agent's professional persona (senior
  recruiter, ATS expert, etc.) with an explicit non-fabrication rule.
- Implements `build_user_prompt(data) -> str`.

## Running an agent

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python -m career_copilot.cli resume_analysis samples/sample_resume.txt
```

Without an API key, see `outputs/*_sample_output.json` for a verified example of
each agent's output shape.

## Design decisions

- **Language/runtime:** Python + the `anthropic` SDK + Pydantic v2 for schema
  validation — chosen for clean structured I/O between agents and minimal
  ceremony per agent.
- **Structured output:** every agent forces a single tool call matching its
  output schema (`core/llm_client.py:run_structured`), so downstream agents
  never depend on parsing prose.
- **Verification:** each agent ships with a fixture input and a sample output
  reviewed before the next agent is built (see Status table above).
- **Research-grounded agents:** agents whose subject is the real world rather
  than a document the user provided (e.g. Company Intelligence) run in two
  phases — a research call with Anthropic's server-side `web_search` tool,
  then a non-searching structuring call — so fabrication risk on real facts
  stays low and every claim can be traced to a cited source.
- **Extraction vs. synthesis agents:** agents 1-7 take raw source text
  (resume/JD) and re-derive their own findings independently — this keeps
  them testable in isolation and lets a later Supervisor/Critic agent
  cross-check their outputs for consistency rather than trusting one agent's
  chain blindly. Agent 8 (Portfolio Recommendation) is the first pure
  synthesis agent: it takes an already-identified list of gaps (typically
  sourced from Gap Analysis / Skill Evidence) rather than re-reading the
  resume, since its job is generative, not extractive.
- **Reporting:** agents return JSON for machine consumption; the Final Report
  Agent (agent 15) is responsible for rendering the consolidated HTML dashboard.
- **Orchestration layer (agents 16-18):** Planner, Critic, and Supervisor don't
  analyze resumes/JDs/companies themselves — they reason about the *other 15
  agents*. Their shared ground truth is `core/registry.py`'s `AGENT_REGISTRY`,
  a machine-readable catalog of every agent's required/optional inputs and
  real dependencies, built directly from how each agent is implemented. This
  makes it structurally impossible for the orchestration layer to invent an
  agent that doesn't exist or a dependency edge that isn't real — Planner
  Agent's sample plan had every `agent_id` and `depends_on` reference
  programmatically checked against the registry before being accepted.
