# Critic Agent

**Agent ID:** `critic` · **Category:** Orchestration · **Module:** `career_copilot/agents/critic.py`

## Purpose

Reviews and validates every other content agent's real output before it reaches the user — checking facts and internal arithmetic, not just prose quality.

## Problem it solves

An LLM system that never checks its own work will eventually ship a confident, wrong, or internally-inconsistent output. This agent is the check.

## Target users

The system itself, as a quality gate; developers wanting an honest audit of agent output quality.

## Workflow

Single-pass: takes the actual JSON output (not summaries) of up to 15 reviewed agents, cross-checks claims against resume/JD ground truth, recomputes stated totals against their own line items, and scores 10 dimensions per agent. Grounded in `AGENT_REGISTRY` so it can't review or reference an agent that doesn't exist.

## Inputs (`CriticInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `Optional[str]` | `None` |
| `company_name` | `Optional[str]` | `None` |
| `resume_analysis_output` | `Optional[str]` | `None` |
| `jd_intelligence_output` | `Optional[str]` | `None` |
| `company_intelligence_output` | `Optional[str]` | `None` |
| `ats_optimization_output` | `Optional[str]` | `None` |
| `resume_rewrite_output` | `Optional[str]` | `None` |
| `gap_analysis_output` | `Optional[str]` | `None` |
| `skill_evidence_output` | `Optional[str]` | `None` |
| `portfolio_recommendation_output` | `Optional[str]` | `None` |
| `learning_certification_output` | `Optional[str]` | `None` |
| `recruiter_simulation_output` | `Optional[str]` | `None` |
| `interview_coach_output` | `Optional[str]` | `None` |
| `linkedin_optimization_output` | `Optional[str]` | `None` |
| `application_assets_output` | `Optional[str]` | `None` |
| `career_strategy_output` | `Optional[str]` | `None` |
| `final_report_output` | `Optional[str]` | `None` |

## Outputs (`CriticOutput`)

| Field | Type |
|---|---|
| `agent_reviews` | `List[AgentReview]` |
| `final_verdict` | `FinalVerdict` |
| `human_readable_summary` | `str` |
| `review_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- A single review pass — does not re-run any upstream agent or independently re-search facts outside what those agents themselves cited.
- 10-dimension scoring involves judgment calls; a different reviewer could land on adjacent but not identical scores.

## Future improvements

- Track score trends across runs of the same agent over time to detect prompt-change regressions automatically.
