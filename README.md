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
| 9 | Learning & Certification Agent | ⏳ Not started |
| 10 | Recruiter Simulation Agent | ⏳ Not started |
| 11 | Interview Coach Agent | ⏳ Not started |
| 12 | LinkedIn Optimization Agent | ⏳ Not started |
| 13 | Application Assets Agent | ⏳ Not started |
| 14 | Career Strategy Agent | ⏳ Not started |
| 15 | Final Report Agent | ⏳ Not started |
| 16 | Planner Agent | ⏳ Not started |
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
  agents/
    resume_analysis.py       # Agent 1
    jd_intelligence.py       # Agent 2
    company_intelligence.py  # Agent 3 — two-phase: web research, then structure
    ats_optimization.py      # Agent 4
    resume_rewrite.py        # Agent 5
    gap_analysis.py           # Agent 6
    skill_evidence.py         # Agent 7
    portfolio_recommendation.py  # Agent 8 — takes structured gaps, not a raw document
  cli.py              # run a single agent from the command line (docs-only agents)
samples/
  sample_resume.txt   # fixture used to verify agents 1, 4, 5, 6, 7
  sample_jd.txt        # fixture used to verify agents 2, 4, 5, 6, 7 (paired with sample_resume.txt's PM/fintech profile)
outputs/
  resume_analysis_sample_output.{json,md}     # verified sample output, agent 1
  jd_intelligence_sample_output.{json,md}      # verified sample output, agent 2
  company_intelligence_sample_output.{json,md} # verified sample output, agent 3
  ats_optimization_sample_output.{json,md}     # verified sample output, agent 4
  resume_rewrite_sample_output.{json,md}       # verified sample output, agent 5
  gap_analysis_sample_output.{json,md}         # verified sample output, agent 6
  skill_evidence_sample_output.{json,md}       # verified sample output, agent 7
  portfolio_recommendation_sample_output.{json,md} # verified sample output, agent 8
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
