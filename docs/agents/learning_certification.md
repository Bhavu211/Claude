# Learning & Certification Agent

**Agent ID:** `learning_certification` · **Category:** Research · **Module:** `career_copilot/agents/learning_certification.py`

## Purpose

Builds a sequenced learning roadmap and grades certification ROI, grounded in live web research into real, currently-existing courses and programs.

## Problem it solves

Generic advice ('learn SQL') doesn't say which course, how long it actually takes, or whether a certification is worth the money for this specific candidate and role — this agent answers all three with real, cited resources.

## Target users

Job seekers planning how to close a skill gap; Career Strategy Agent downstream.

## Workflow

Two-phase like Company Intelligence: live web research into real resources, then a structuring pass. Depends on Gap Analysis and Skill Evidence for its `missing_competencies` input.

This is a **research-grounded** agent: it makes a live `web_search`-enabled call first, then a separate non-searching structuring call, to keep 'did we research this' and 'did we format this correctly' as independent concerns.

## Inputs (`LearningCertificationInput`)

| Field | Type | Default |
|---|---|---|
| `target_role` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `missing_competencies` | `List[str]` | *required* |
| `certifications_under_consideration` | `List[str]` | `list()` |
| `candidate_background` | `Optional[str]` | `None` |

## Outputs (`LearningCertificationOutput`)

| Field | Type |
|---|---|
| `target_role` | `str` |
| `company_name` | `Optional[str]` |
| `competency_plans` | `List[CompetencyPlan]` |
| `certification_assessments` | `List[CertificationAssessment]` |
| `overall_learning_roadmap` | `str` |
| `total_estimated_time` | `Optional[str]` |
| `sources` | `List[SourceRef]` |
| `human_readable_summary` | `str` |
| `plan_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Certification ROI grading is time-sensitive — program value and reputation shift.
- A prior sample run had a genuine arithmetic bug (a stated total that didn't match its own line items) — caught by Critic Agent and fixed. A reminder that summary-level numbers need active reconciliation against the numbers they summarize, not just narrative review.

## Future improvements

- Auto-validate that `total_estimated_time` always equals the sum of `competency_plans[*].estimated_time` before returning.
