# Resume Analysis Agent

**Agent ID:** `resume_analysis` · **Category:** Extraction · **Module:** `career_copilot/agents/resume_analysis.py`

## Purpose

Extracts structured, evidence-based signal from a raw resume — experience, skills, quantified achievements, and writing-quality issues — without judging fit against any specific role.

## Problem it solves

Resumes are unstructured prose. Every downstream agent (ATS scoring, gap analysis, rewriting) needs a reliable structured read of what the resume actually says, not a fresh re-interpretation each time.

## Target users

Job seekers wanting an honest inventory of their resume's content; downstream agents in this system.

## Workflow

Single-pass: resume text in, structured extraction out. No web research, no other agent's output required.

## Inputs (`ResumeAnalysisInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `candidate_name` | `Optional[str]` | `None` |

## Outputs (`ResumeAnalysisOutput`)

| Field | Type |
|---|---|
| `candidate_name` | `Optional[str]` |
| `summary` | `Optional[str]` |
| `work_experience` | `List[WorkExperienceEntry]` |
| `projects` | `List[ProjectEntry]` |
| `skills` | `SkillsBlock` |
| `certifications` | `List[CertificationEntry]` |
| `education` | `List[EducationEntry]` |
| `achievements` | `List[AchievementEntry]` |
| `leadership_experience` | `List[str]` |
| `product_experience` | `List[str]` |
| `technical_experience` | `List[str]` |
| `metrics` | `List[ExtractedMetric]` |
| `domains` | `List[str]` |
| `total_years_experience_estimate` | `Optional[float]` |
| `strongest_achievements` | `List[str]` |
| `weakest_sections` | `List[str]` |
| `missing_metrics` | `List[str]` |
| `redundant_content` | `List[str]` |
| `weak_action_verbs` | `List[QualityIssue]` |
| `grammar_issues` | `List[QualityIssue]` |
| `ats_formatting_issues` | `List[QualityIssue]` |
| `human_readable_summary` | `str` |
| `analysis_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Cannot verify claims against reality — it extracts what the resume states, not what's true.
- Years-of-experience estimates depend on how 'Present' is resolved, which isn't always explicit.
- Cannot see resume layout/formatting (columns, tables, images) — text-only input.

## Future improvements

- Accept PDF/DOCX input directly instead of requiring pre-extracted text.
- Add a companion 'estimate_as_of_date' field so time-based estimates carry their own assumption.
