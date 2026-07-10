# Application Assets Agent

**Agent ID:** `application_assets` · **Category:** Extraction · **Module:** `career_copilot/agents/application_assets.py`

## Purpose

Drafts the full set of application communication: cover letter, cold outreach, LinkedIn connection request, referral request, interview follow-up, and thank-you email.

## Problem it solves

Each of these has to be written from scratch, tailored, and kept factually consistent with the resume and JD — tedious and error-prone to do by hand for every application.

## Target users

Job seekers preparing a full application package.

## Workflow

Single-pass: resume text (+ optional JD, company context, contact names) in, six drafted assets out, with bracketed placeholders (e.g. `[Recruiter Name]`) wherever specific facts weren't provided rather than invented.

## Inputs (`ApplicationAssetsInput`)

| Field | Type | Default |
|---|---|---|
| `resume_text` | `str` | *required* |
| `jd_text` | `Optional[str]` | `None` |
| `target_role` | `Optional[str]` | `None` |
| `company_name` | `Optional[str]` | `None` |
| `company_context` | `Optional[str]` | `None` |
| `recruiter_or_hiring_manager_name` | `Optional[str]` | `None` |
| `referral_contact_name` | `Optional[str]` | `None` |
| `referral_contact_relationship` | `Optional[str]` | `None` |
| `interview_discussion_notes` | `Optional[str]` | `None` |

## Outputs (`ApplicationAssetsOutput`)

| Field | Type |
|---|---|
| `cover_letter` | `ApplicationAsset` |
| `recruiter_outreach_message` | `ApplicationAsset` |
| `linkedin_connection_request` | `ApplicationAsset` |
| `referral_request` | `ApplicationAsset` |
| `follow_up_email` | `ApplicationAsset` |
| `thank_you_email` | `ApplicationAsset` |
| `human_readable_summary` | `str` |
| `generation_confidence` | `ConfidenceLevel` |
| `limitations` | `List[str]` |

## Limitations

- Placeholder count and platform character limits (e.g. LinkedIn's 300-char connection request) are load-bearing correctness properties — worth spot-checking after any prompt change, since they were specifically what Critic Agent verified by recount.
- Tone/voice choices are a single agent's judgment; some users will want a different register (more formal, more casual).

## Future improvements

- Let the user select a tone preset (formal / warm / concise) per asset.
