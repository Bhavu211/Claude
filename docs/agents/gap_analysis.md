# Gap Analysis Agent

**Agent ID:** `gap_analysis` · **Category:** Extraction · **Module:** `career_copilot/agents/gap_analysis.py`

## Purpose

Compares the resume against the JD requirement-by-requirement: is each requirement present, how strong is the evidence, how severe is the gap if it's missing.

## Problem it solves

Candidates often don't know exactly which JD requirements they're weak on until a recruiter rejects them — this surfaces it in advance, specifically and actionably.

## Target users

Job seekers deciding what to address before applying; Portfolio Recommendation, Learning & Certification, and Career Strategy agents downstream.

## Workflow

Single-pass: resume + JD text in, a row-by-row requirement table out.

## Inputs (`GapAnalysisInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `str` | *required* |

## Outputs (`GapAnalysisOutput`)

| Field | Type |
|---|---|
| `role_title` | `Optional[str]` |
| `company_name` | `Optional[str]` |
| `rows` | `List[GapAnalysisRow]` |
| `strongest_matches` | `List[str]` |
| `critical_gaps` | `List[str]` |
| `overall_fit_assessment` | `str` |
| `human_readable_summary` | `str` |
| `analysis_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Only as good as what the resume actually states — cannot credit unstated experience.
- Severity judgments are relative to the stated JD, not the broader industry norm.

## Future improvements

- Weight gap severity by how frequently that requirement appears across similar JDs, not just this one posting.
