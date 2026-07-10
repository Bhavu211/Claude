# Planner Agent

**Agent ID:** `planner` · **Category:** Orchestration · **Module:** `career_copilot/agents/planner.py`

## Purpose

Detects user intent and decides which of the 15 specialist agents to run (and which to skip, and why), sequences them into dependency-respecting parallel groups, flags missing inputs, and estimates cost.

## Problem it solves

Running all 18 agents for every request is wasteful, and running them in the wrong order wastes even more — this agent decides the minimum correct plan for what the user actually asked for.

## Target users

The system itself, as the entry point that decides what to run before anything runs.

## Workflow

Single-pass: grounded entirely in `AGENT_REGISTRY` (core/registry.py), the machine-readable catalog of every agent's requirements and dependencies — never free-associates about what agents 'probably' exist.

## Inputs (`PlannerInput`)

| Field | Type | Default |
|---|---|---|
| `user_goal` | `str` | *required* |
| `has_resume` | `bool` | *required* |
| `has_jd` | `bool` | `False` |
| `has_company_name` | `bool` | `False` |
| `years_of_experience_provided` | `bool` | `False` |
| `previous_outputs_available` | `List[str]` | `list()` |

## Outputs (`PlannerOutput`)

| Field | Type |
|---|---|
| `user_intent` | `UserIntent` |
| `execution_plan` | `List[AgentExecutionItem]` |
| `parallel_groups` | `List[ParallelGroup]` |
| `missing_inputs` | `List[MissingInput]` |
| `conflicts_resolved` | `List[ConflictResolution]` |
| `estimated_completion` | `ExecutionCostEstimate` |
| `risks` | `List[str]` |
| `final_execution_strategy` | `str` |
| `human_readable_summary` | `str` |
| `planning_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Time estimates assume agents within a parallel group can run concurrently in the execution environment; if execution is strictly sequential, actual time is closer to the sum of all agents' individual runtimes.
- Does not itself resolve conflicts that arise mid-execution (e.g. two agents' actual outputs disagreeing once run) — that's Supervisor Agent's job downstream.

## Future improvements

- Feed back actual measured execution times per agent to refine future cost estimates.
