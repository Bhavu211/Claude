# Portfolio Recommendation Agent

**Agent ID:** `portfolio_recommendation` · **Category:** Synthesis · **Module:** `career_copilot/agents/portfolio_recommendation.py`

## Purpose

Designs concrete portfolio projects to close specific, already-identified skill gaps — a synthesis agent, not an extraction agent.

## Problem it solves

'Build a portfolio project' is generic advice. This agent turns identified gaps into a specific, scoped project brief (problem, users, features, tech stack, MVP, KPIs) a candidate can actually execute.

## Target users

Job seekers who need to demonstrate a skill they can't yet claim from work history.

## Workflow

Single-pass synthesis: takes `gaps_to_close` (a structured list, typically from Gap Analysis / Skill Evidence output) — not raw resume text — and a target role/company.

## Inputs (`PortfolioRecommendationInput`)

| Field | Type | Default |
|---|---|---|
| `target_role` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `gaps_to_close` | `List[str]` | *required* |
| `candidate_background` | `Optional[str]` | `None` |
| `max_projects` | `int` | `3` |

## Outputs (`PortfolioRecommendationOutput`)

| Field | Type |
|---|---|
| `target_role` | `str` |
| `company_name` | `Optional[str]` |
| `projects` | `List[PortfolioProject]` |
| `gaps_not_addressed` | `List[str]` |
| `human_readable_summary` | `str` |
| `recommendation_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Declines to portfolio-ize gaps that a solo project genuinely can't substitute for (e.g. a mentoring gap) rather than force-fitting a project onto every gap.
- Build-time estimates may run optimistic for a candidate working full-time (a real Critic Agent finding).

## Future improvements

- Widen build-time estimates or caveat them explicitly as assuming dedicated weekend time.
- Link each project's `addresses_gaps` back to the exact Gap Analysis row it targets for full traceability.
