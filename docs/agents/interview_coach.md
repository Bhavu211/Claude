# Interview Coach Agent

**Agent ID:** `interview_coach` · **Category:** Extraction · **Module:** `career_copilot/agents/interview_coach.py`

## Purpose

Generates HR/behavioral/technical/product/company-specific interview questions, each with a resume-backed STAR answer — or an honest null if the resume doesn't support one.

## Problem it solves

Generic interview-prep questions don't map to a candidate's actual background, and generic 'sample answers' invite candidates to rehearse claims they can't actually back up in a follow-up question.

## Target users

Job seekers preparing for interviews.

## Workflow

Single-pass: resume + JD text (+ optional company context from Company Intelligence) in, question sets with grounded STAR answers out.

## Inputs (`InterviewCoachInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `company_context` | `Optional[str]` | `None` |

## Outputs (`InterviewCoachOutput`)

| Field | Type |
|---|---|
| `hr_questions` | `List[InterviewQuestion]` |
| `behavioral_questions` | `List[InterviewQuestion]` |
| `technical_questions` | `List[InterviewQuestion]` |
| `product_questions` | `List[InterviewQuestion]` |
| `company_specific_questions` | `List[InterviewQuestion]` |
| `preparation_priorities` | `List[str]` |
| `human_readable_summary` | `str` |
| `prep_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Where the resume has no evidence for a likely behavioral question (e.g. a mentoring story), the STAR answer is explicitly null rather than fabricated — the highest-stakes place in the whole system for fabrication risk, and the one most carefully guarded.
- Company-specific questions are only as good as the Company Intelligence context provided; without it, this agent falls back to JD-text-only grounding.

## Future improvements

- Add a mock-interview mode that asks the generated questions interactively and critiques the candidate's typed answer.
