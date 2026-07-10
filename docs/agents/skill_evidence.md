# Skill Evidence Agent

**Agent ID:** `skill_evidence` · **Category:** Extraction · **Module:** `career_copilot/agents/skill_evidence.py`

## Purpose

Grades evidence *strength*, not just presence, for every skill-shaped JD requirement — the difference between 'mentioned' and 'demonstrated with a specific bullet.'

## Problem it solves

Gap Analysis answers 'is this skill present.' It doesn't answer 'would a skeptical recruiter actually believe this skill, based on how it's written.' This agent answers that second, harder question.

## Target users

Job seekers wanting to know which skills need a stronger bullet, not just a mention; Portfolio Recommendation and Learning & Certification agents downstream.

## Workflow

Single-pass: resume + JD text in, a confidence-graded skill table out.

## Inputs (`SkillEvidenceInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `str` | *required* |

## Outputs (`SkillEvidenceOutput`)

| Field | Type |
|---|---|
| `role_title` | `Optional[str]` |
| `company_name` | `Optional[str]` |
| `skills` | `List[SkillEvidenceItem]` |
| `well_evidenced_skills` | `List[str]` |
| `weakly_evidenced_skills` | `List[str]` |
| `overall_evidence_strength` | `str` |
| `human_readable_summary` | `str` |
| `analysis_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Confidence grading is a judgment call about how convincing evidence reads, not an objective measurement.
- Deliberately excludes years-of-experience style requirements (not skill-shaped) from its scope.

## Future improvements

- Suggest a specific rewritten bullet for each LOW/NONE-confidence skill, not just flag the gap.
