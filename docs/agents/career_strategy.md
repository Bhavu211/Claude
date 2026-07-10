# Career Strategy Agent

**Agent ID:** `career_strategy` · **Category:** Research · **Module:** `career_copilot/agents/career_strategy.py`

## Purpose

Advises on role fit, live-researched market salary, seniority evaluation, promotion readiness, and a 30/90/365-day action plan.

## Problem it solves

'Should I take this role' and 'what should I do in my first year' are the highest-stakes questions in a job search, and generic advice ignores the candidate's actual specific gaps and strengths.

## Target users

Job seekers deciding whether/how to pursue a role; the capstone synthesis before Final Report.

## Workflow

Two-phase like Company Intelligence: live web research (notably for salary data), then structuring. Depends on Gap Analysis, Skill Evidence, Recruiter Simulation, Portfolio Recommendation, and Learning & Certification to synthesize rather than re-deriving fit from scratch.

This is a **research-grounded** agent: it makes a live `web_search`-enabled call first, then a separate non-searching structuring call, to keep 'did we research this' and 'did we format this correctly' as independent concerns.

## Inputs (`CareerStrategyInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `target_role` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `location` | `Optional[str]` | `None` |
| `key_findings_summary` | `Optional[str]` | `None` |
| `portfolio_and_learning_plan_summary` | `Optional[str]` | `None` |

## Outputs (`CareerStrategyOutput`)

| Field | Type |
|---|---|
| `role_fit_assessment` | `FitLevel` |
| `role_fit_reasoning` | `str` |
| `market_salary_estimate` | `SalaryEstimate` |
| `seniority_evaluation` | `str` |
| `seniority_evidence` | `str` |
| `promotion_readiness_summary` | `str` |
| `promotion_blockers` | `List[str]` |
| `promotion_accelerants` | `List[str]` |
| `career_risks` | `List[RankedItem]` |
| `career_opportunities` | `List[RankedItem]` |
| `thirty_day_plan` | `List[ActionPlanItem]` |
| `ninety_day_plan` | `List[ActionPlanItem]` |
| `one_year_roadmap` | `List[ActionPlanItem]` |
| `sources` | `List[SourceRef]` |
| `human_readable_summary` | `str` |
| `strategy_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Salary estimates explicitly disclose when sources disagree substantially, rather than presenting a falsely precise single number.
- Synthesizes 5 upstream agents' findings — an error in any of them propagates here uncorrected.

## Future improvements

- Add geographic cost-of-living adjustment to salary estimates when location differs from the researched sample.
