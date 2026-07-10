# ATS Optimization Agent

**Agent ID:** `ats_optimization` · **Category:** Extraction · **Module:** `career_copilot/agents/ats_optimization.py`

## Purpose

Scores a resume's ATS (Applicant Tracking System) compatibility and, when a JD is provided, its keyword coverage against that specific posting.

## Problem it solves

Well-written resumes get silently rejected by ATS parsers due to formatting/structure issues invisible to the human eye reading plain text.

## Target users

Job seekers before submitting an application.

## Workflow

Single-pass: resume text (+ optional JD/target role) in, score + itemized deductions out.

## Inputs (`ATSOptimizationInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `Optional[str]` | `None` |
| `target_role` | `Optional[str]` | `None` |

## Outputs (`ATSOptimizationOutput`)

| Field | Type |
|---|---|
| `ats_compatibility_score` | `int` |
| `score_reasoning` | `str` |
| `structure_assessment` | `List[SectionCheck]` |
| `section_hierarchy_issues` | `List[QualityIssue]` |
| `parsing_compatibility_issues` | `List[QualityIssue]` |
| `formatting_issues` | `List[QualityIssue]` |
| `skills_placement_notes` | `List[str]` |
| `keyword_coverage` | `List[KeywordCoverageItem]` |
| `keyword_coverage_summary` | `Optional[str]` |
| `keyword_density_notes` | `List[str]` |
| `readability_notes` | `List[str]` |
| `prioritized_recommendations` | `List[QualityIssue]` |
| `human_readable_summary` | `str` |
| `analysis_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Cannot assess true layout-level ATS risk (columns, tables, text boxes) from plain text alone — explicitly refuses to guess at this rather than fabricate a layout judgment.
- Keyword coverage reflects the *given* JD only, not general ATS keyword libraries.

## Future improvements

- Accept the original file format (PDF/DOCX) to assess real layout risk, not just text.
- Support multiple ATS vendor profiles (Workday, Greenhouse, Taleo differ in parsing behavior).
