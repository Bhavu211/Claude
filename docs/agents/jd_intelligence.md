# JD Intelligence Agent

**Agent ID:** `jd_intelligence` · **Category:** Extraction · **Module:** `career_copilot/agents/jd_intelligence.py`

## Purpose

Decodes a job description into prioritized requirements, hidden expectations, and what a recruiter is actually screening for beneath the boilerplate.

## Problem it solves

Job descriptions bury the 2-3 things that actually matter under generic corporate language. Candidates waste effort optimizing for requirements that don't move the needle.

## Target users

Job seekers deciding what to emphasize; Gap Analysis, Skill Evidence, and Resume Rewrite agents downstream.

## Workflow

Single-pass: JD text in, structured requirement breakdown out.

## Inputs (`JDIntelligenceInput`)

| Field | Type | Default |
|---|---|---|
| `jd_text` | `str` | *required* |
| `company_name` | `Optional[str]` | `None` |
| `role_title` | `Optional[str]` | `None` |

## Outputs (`JDIntelligenceOutput`)

| Field | Type |
|---|---|
| `role_title` | `Optional[str]` |
| `company_name` | `Optional[str]` |
| `seniority_level` | `Optional[str]` |
| `years_of_experience_required` | `Optional[str]` |
| `requirements` | `List[ClassifiedRequirement]` |
| `responsibilities` | `List[str]` |
| `kpis` | `List[str]` |
| `hidden_expectations` | `List[HiddenExpectation]` |
| `recruiter_intent` | `str` |
| `hiring_priorities` | `List[str]` |
| `human_readable_summary` | `str` |
| `analysis_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Hidden expectations are inferred, not confirmed — always flagged as inference, never presented as fact.
- Cannot know a company's actual, unwritten hiring bar — only what the JD text signals.

## Future improvements

- Cross-reference against multiple JD postings for the same role to detect boilerplate vs. genuine signal.
- Tighten hiring_priorities to avoid restating requirements verbatim (a real Critic Agent finding).
