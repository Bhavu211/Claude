# Final Report Agent

**Agent ID:** `final_report` · **Category:** Report · **Module:** `career_copilot/agents/final_report.py`

## Purpose

Consolidates every upstream agent's summary into one coherent, non-duplicative executive report and readiness dashboard.

## Problem it solves

14 separate agent outputs are too much for a candidate to read end-to-end and synthesize themselves — this agent does that synthesis work, introducing zero new facts of its own.

## Target users

Job seekers wanting one final, readable deliverable instead of 14 separate JSON files.

## Workflow

Single-pass synthesis: takes structured summaries and specific typed fields (ATS score, gap stats, recruiter recommendation, role fit, salary range) from up to 14 upstream agents.

## Inputs (`FinalReportInput`)

| Field | Type | Default |
|---|---|---|
| `candidate_name` | `str` | *required* |
| `target_role` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `resume_analysis_summary` | `Optional[str]` | `None` |
| `jd_intelligence_summary` | `Optional[str]` | `None` |
| `company_intelligence_summary` | `Optional[str]` | `None` |
| `ats_optimization_summary` | `Optional[str]` | `None` |
| `resume_rewrite_summary` | `Optional[str]` | `None` |
| `gap_analysis_summary` | `Optional[str]` | `None` |
| `skill_evidence_summary` | `Optional[str]` | `None` |
| `portfolio_recommendation_summary` | `Optional[str]` | `None` |
| `learning_certification_summary` | `Optional[str]` | `None` |
| `recruiter_simulation_summary` | `Optional[str]` | `None` |
| `interview_coach_summary` | `Optional[str]` | `None` |
| `linkedin_optimization_summary` | `Optional[str]` | `None` |
| `application_assets_summary` | `Optional[str]` | `None` |
| `career_strategy_summary` | `Optional[str]` | `None` |
| `ats_score` | `Optional[int]` | `None` |
| `gap_analysis_stats` | `Optional[str]` | `None` |
| `recruiter_recommendation` | `Optional[str]` | `None` |
| `role_fit` | `Optional[str]` | `None` |
| `salary_range` | `Optional[str]` | `None` |

## Outputs (`FinalReportOutput`)

| Field | Type |
|---|---|
| `candidate_name` | `str` |
| `target_role` | `str` |
| `company_name` | `Optional[str]` |
| `executive_summary` | `str` |
| `resume_strengths` | `List[str]` |
| `resume_weaknesses` | `List[str]` |
| `jd_match_analysis` | `str` |
| `company_insights` | `str` |
| `ats_analysis` | `str` |
| `gap_analysis` | `str` |
| `learning_roadmap` | `str` |
| `portfolio_recommendations` | `str` |
| `certification_roadmap` | `str` |
| `interview_preparation` | `str` |
| `linkedin_optimization` | `str` |
| `application_assets` | `str` |
| `final_readiness_dashboard` | `FinalReadinessDashboard` |
| `prioritized_next_steps` | `List[PrioritizedNextStep]` |
| `coherence_check` | `List[str]` |
| `human_readable_summary` | `str` |
| `report_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Does not independently re-verify any upstream agent's claims — an error upstream carries through unchanged.
- The top-line 'overall_readiness_status' can read more positive than individual metrics beneath it suggest if a reader only skims the headline (a real Critic Agent finding).

## Future improvements

- Keep warning-level metric callouts visually adjacent to the top-line status badge rather than requiring a scroll to see them.
