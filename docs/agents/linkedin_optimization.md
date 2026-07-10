# LinkedIn Optimization Agent

**Agent ID:** `linkedin_optimization` · **Category:** Extraction · **Module:** `career_copilot/agents/linkedin_optimization.py`

## Purpose

Rewrites headline, About section, experience bullets, skills ordering, and Featured section recommendations for LinkedIn's specific conventions and algorithm.

## Problem it solves

A resume and a LinkedIn profile serve different purposes (application vs. discoverability/networking) but candidates often just paste one into the other, losing effectiveness on both.

## Target users

Job seekers optimizing their LinkedIn presence.

## Workflow

Single-pass: resume text (+ optional JD/role/company, and portfolio project titles from Portfolio Recommendation) in, LinkedIn-specific copy out.

## Inputs (`LinkedInOptimizationInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `Optional[str]` | `None` |
| `target_role` | `Optional[str]` | `None` |
| `company_name` | `Optional[str]` | `None` |
| `portfolio_project_titles` | `List[str]` | `list()` |

## Outputs (`LinkedInOptimizationOutput`)

| Field | Type |
|---|---|
| `headline` | `LinkedInHeadline` |
| `about` | `LinkedInAbout` |
| `experience_entries` | `List[LinkedInExperienceEntry]` |
| `skills` | `SkillsSection` |
| `featured_recommendations` | `List[FeaturedRecommendation]` |
| `alignment_notes` | `List[str]` |
| `authenticity_check` | `List[str]` |
| `human_readable_summary` | `str` |
| `optimization_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Skills ranking follows Skill Evidence Agent's confidence grading rather than optimizing purely for JD keyword match — this is a deliberate evidence-honesty choice, not an SEO-maximizing one.
- Cannot account for LinkedIn's actual current search/ranking algorithm, which isn't public and changes over time.

## Future improvements

- Add character-count validation against LinkedIn's current field limits (headline, About) as a hard schema constraint, not just a note.
