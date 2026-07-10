# Supervisor Agent

**Agent ID:** `supervisor` · **Category:** Orchestration · **Module:** `career_copilot/agents/supervisor.py`

## Purpose

The top-level entry point: cross-checks Planner's execution plan against what actually ran, cross-checks Critic's findings against what's been fixed, and renders a single go/no-go delivery verdict.

## Problem it solves

Even with a good plan and a good review, someone has to actually decide 'is this package ready to hand to the user' — and that decision needs to follow strictly from what happened, not from a general vibe that things are probably fine.

## Target users

The system itself, as the final gate before a deliverable is considered ready; developers wanting a single ready/not-ready signal instead of parsing 17 agents' outputs by hand.

## Workflow

Single-pass: takes Planner's output, Critic's output, the actual list of agents that completed, and any fixes applied post-review. Never marks an issue resolved without a specific, matching fix description.

## Inputs (`SupervisorInput`)

| Field | Type | Default |
|---|---|---|
| `candidate_name` | `str` | *required* |
| `target_role` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `user_goal` | `str` | *required* |
| `planner_output` | `str` | *required* |
| `completed_agent_ids` | `List[str]` | `list()` |
| `failed_agent_ids` | `List[str]` | `list()` |
| `critic_output` | `Optional[str]` | `None` |
| `post_critic_fixes_applied` | `List[str]` | `list()` |
| `final_report_output` | `Optional[str]` | `None` |

## Outputs (`SupervisorOutput`)

| Field | Type |
|---|---|
| `session_status` | `SessionStatus` |
| `orchestration_log` | `List[OrchestrationRecord]` |
| `plan_adherence_issues` | `List[str]` |
| `quality_gate` | `QualityGateStatus` |
| `issue_resolutions` | `List[IssueResolution]` |
| `open_blocking_issues` | `List[str]` |
| `final_deliverable_ready` | `bool` |
| `preserved_limitations` | `List[str]` |
| `next_actions` | `List[str]` |
| `human_readable_summary` | `str` |
| `supervisor_confidence` | `ConfidenceLevel` |

## Limitations

- If Critic's review wasn't run at all, this agent explicitly declines to treat the system as clean — it lets that absence drive the quality gate downward rather than defaulting to 'passed.'
- Carries forward, rather than independently re-verifies, every limitation the other agents raised.

## Future improvements

- Support partial re-runs: re-invoke only the specific agents flagged with unresolved issues, rather than requiring a full pipeline re-run.
