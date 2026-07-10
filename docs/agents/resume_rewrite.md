# Resume Rewrite Agent

**Agent ID:** `resume_rewrite` · **Category:** Extraction · **Module:** `career_copilot/agents/resume_rewrite.py`

## Purpose

Rewrites the resume into ATS/Recruiter/Startup/Enterprise/Executive versions while keeping every underlying fact unchanged.

## Problem it solves

One resume rarely fits every audience — an ATS-optimized version and a narrative recruiter-facing version have different needs, but hand-rewriting each is slow and risks introducing exaggeration.

## Target users

Job seekers tailoring applications to different companies/channels.

## Workflow

Single-pass: resume text (+ optional JD/role/company) in, multiple rewritten versions out.

## Inputs (`ResumeRewriteInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `Optional[str]` | `None` |
| `target_role` | `Optional[str]` | `None` |
| `company_name` | `Optional[str]` | `None` |

## Outputs (`ResumeRewriteOutput`)

| Field | Type |
|---|---|
| `candidate_name` | `Optional[str]` |
| `target_role` | `Optional[str]` |
| `versions` | `List[ResumeVersion]` |
| `global_changes_summary` | `List[str]` |
| `unmet_improvement_opportunities` | `List[UnmetImprovementOpportunity]` |
| `human_readable_summary` | `str` |
| `rewrite_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Declines to generate a version it doesn't have justification for (e.g. an Executive version for a non-executive candidate) rather than force-generating one.
- Verb-choice decisions (e.g. 'Managed' vs 'Owned') sit close to a scope-inflation line and need human judgment on borderline cases.

## Future improvements

- Let the user flag which specific bullets are open to stronger verb framing, rather than the agent deciding alone.
- Add a diff view showing exactly what changed between the original and each rewritten version.
