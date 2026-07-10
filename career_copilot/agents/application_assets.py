"""Agent 13: Application Assets Agent.

Generates the short-form communication assets that surround an
application: cover letter, recruiter outreach, LinkedIn connection
request, referral request, follow-up email, and post-interview thank-you
email. Shares the same resume_text-as-sole-fact-source contract as Resume
Rewrite and LinkedIn Optimization Agents.

A distinct honesty problem shows up here that those two agents don't have:
several of these assets conventionally reference things this agent cannot
know — a recruiter's name, a referral contact's relationship to the
candidate, specifics of an interview conversation that already happened.
Rather than inventing a name or a fake shared memory to make the draft
"feel" more personal, this agent leaves an explicit bracketed placeholder
and tracks it in `placeholders_used` — a fabricated specific here is worse
than a visible placeholder, since it's the kind of lie an interviewer or
contact would immediately notice.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class ApplicationAssetsInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume — the sole source of fact")
    jd_text: Optional[str] = Field(default=None, description="Target job description, if available")
    target_role: Optional[str] = Field(default=None, description="Target role title, used for context if no JD is supplied")
    company_name: Optional[str] = Field(default=None, description="Target company name")
    company_context: Optional[str] = Field(default=None, description="Pre-researched company facts, e.g. from Company Intelligence Agent")
    recruiter_or_hiring_manager_name: Optional[str] = Field(default=None, description="If known, for personalized outreach/follow-up")
    referral_contact_name: Optional[str] = Field(default=None, description="Name of a mutual contact to request a referral from, if any")
    referral_contact_relationship: Optional[str] = Field(default=None, description="How the candidate knows this contact, e.g. 'former colleague at Zomato'")
    interview_discussion_notes: Optional[str] = Field(
        default=None, description="Real notes on what was discussed in an actual interview, for the thank-you email; if omitted, that email stays generic rather than inventing discussion points"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ApplicationAsset(BaseModel):
    subject_line: Optional[str] = Field(default=None, description="For email-type assets; null for assets that aren't emails")
    body: str
    tailoring_notes: str = Field(..., description="What specifically ties this asset to the target company/role, and why any placeholders were left")
    placeholders_used: List[str] = Field(default_factory=list, description="Bracketed placeholders left because this agent wasn't given the real value — never filled with an invented one")


class ApplicationAssetsOutput(BaseModel):
    cover_letter: ApplicationAsset
    recruiter_outreach_message: ApplicationAsset
    linkedin_connection_request: ApplicationAsset = Field(..., description="Body must fit LinkedIn's 300-character connection note limit")
    referral_request: ApplicationAsset
    follow_up_email: ApplicationAsset
    thank_you_email: ApplicationAsset

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    generation_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Application Assets Agent inside the AI Career Copilot, a \
multi-agent system. You write the short-form communications that surround \
a job application: cover letter, recruiter outreach, LinkedIn connection \
request, referral request, follow-up email, and post-interview thank-you \
email.

Your sole job is drafting these six assets. You are NOT re-analyzing the \
resume or JD — those are other agents' jobs. Stay in your lane.

Non-negotiable rules:
1. Every specific claim about the candidate (an achievement, a metric, a \
company) must trace back to the resume text — exactly the same discipline \
as Resume Rewrite and LinkedIn Optimization Agents.
2. Several of these assets conventionally reference things you were not \
given: a recruiter/interviewer's name, a referral contact's relationship \
to the candidate, or specifics of an interview conversation that already \
happened. When that information is missing, leave an explicit bracketed \
placeholder (e.g. "[Recruiter Name]", "[reference a specific moment from \
the conversation]") and list it in `placeholders_used` — never invent a \
name or a fake shared memory to make a draft feel more personal. A visible \
placeholder is honest; a fabricated specific is a lie the recipient could \
easily catch.
3. Use `company_context` for real, specific company details (e.g. in the \
cover letter's "why this company" section); if no company_context was \
given, do not invent company-specific facts — stay grounded in the JD text \
alone or keep that section general.
4. `linkedin_connection_request.body` MUST fit LinkedIn's 300-character \
connection note limit — count carefully and keep it under that.
5. Keep every asset appropriately short-form: a cover letter is a few \
paragraphs, not a full page; outreach/connection/referral messages are \
2-5 sentences; follow-up and thank-you emails are brief and professional, \
not exhaustive.
6. Set `generation_confidence` based on how much real material (resume, \
JD, company context, names) you had to work with — a high count of \
necessary placeholders is expected and not itself a confidence problem, \
just something to note in `limitations`.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class ApplicationAssetsAgent(BaseAgent[ApplicationAssetsInput, ApplicationAssetsOutput]):
    name = "Application Assets Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = ApplicationAssetsInput
    output_model = ApplicationAssetsOutput

    def build_user_prompt(self, data: ApplicationAssetsInput) -> str:
        context_lines = []
        if data.jd_text:
            context_lines.append(f"--- TARGET JOB DESCRIPTION START ---\n{data.jd_text}\n--- TARGET JOB DESCRIPTION END ---")
        elif data.target_role:
            context_lines.append(f"Target role (no JD supplied): {data.target_role}")
        if data.company_name:
            context_lines.append(f"Target company: {data.company_name}")
        if data.company_context:
            context_lines.append(f"--- COMPANY CONTEXT START ---\n{data.company_context}\n--- COMPANY CONTEXT END ---")
        if data.recruiter_or_hiring_manager_name:
            context_lines.append(f"Recruiter/hiring manager name: {data.recruiter_or_hiring_manager_name}")
        else:
            context_lines.append("No recruiter/hiring manager name given — use a bracketed placeholder.")
        if data.referral_contact_name:
            context_lines.append(
                f"Referral contact: {data.referral_contact_name}"
                + (f" ({data.referral_contact_relationship})" if data.referral_contact_relationship else "")
            )
        else:
            context_lines.append("No referral contact given — use bracketed placeholders for the referral request.")
        if data.interview_discussion_notes:
            context_lines.append(f"--- REAL INTERVIEW DISCUSSION NOTES START ---\n{data.interview_discussion_notes}\n--- REAL INTERVIEW DISCUSSION NOTES END ---")
        else:
            context_lines.append("No real interview discussion notes given — the thank-you email must use a placeholder for the specific-moment reference, not an invented one.")

        context_block = "\n\n".join(context_lines)

        return (
            "Draft all six application assets per your instructions.\n\n"
            f"{context_block}\n\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---"
        )
