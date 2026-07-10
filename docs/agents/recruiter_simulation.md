# Recruiter Simulation Agent

**Agent ID:** `recruiter_simulation` · **Category:** Extraction · **Module:** `career_copilot/agents/recruiter_simulation.py`

## Purpose

Simulates a recruiter's blunt, time-pressured 30-second first-pass resume screen — the gut-check most candidates never get to see.

## Problem it solves

Candidates optimize for what they think matters, not what an actual overworked recruiter notices in the first 30 seconds. This surfaces that gap directly.

## Target users

Job seekers wanting a realistic, unflattering-if-necessary read before submitting.

## Workflow

Single-pass: resume + JD text (+ optional company) in, a screening verdict with both shortlist and reject reasons out.

## Inputs (`RecruiterSimulationInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |

## Outputs (`RecruiterSimulationOutput`)

| Field | Type |
|---|---|
| `first_impression` | `str` |
| `strengths` | `List[str]` |
| `concerns` | `List[str]` |
| `missing_information` | `List[str]` |
| `likely_interview_questions` | `List[str]` |
| `reasons_to_shortlist` | `List[str]` |
| `reasons_to_reject` | `List[str]` |
| `hiring_recommendation` | `ScreeningDecision` |
| `recommendation_reasoning` | `str` |
| `human_readable_summary` | `str` |
| `simulation_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- One simulated recruiter's read, not a survey of many — tone and threshold are a design choice, not a guarantee of how any specific real recruiter will react.
- Cannot account for internal referral bias, quota pressure, or other non-resume factors that affect real screening.

## Future improvements

- Offer multiple recruiter personas (agency recruiter vs. in-house vs. hiring manager) with different priorities.
