"""Agent 5: Resume Rewrite Agent.

Acts as an executive resume writer. Produces multiple audience-tailored
rewrites of the same resume — ATS, Recruiter, Startup, Enterprise, and
(when the candidate's level warrants it) Executive — while treating the
original resume text as the sole source of fact.

The versions differ in tone, ordering, and emphasis, never in the underlying
facts: no version may add an employer, title, date, metric, or scope that
isn't in the source resume. Where a bullet could be stronger with a metric
the source doesn't provide, that's recorded in
`unmet_improvement_opportunities` instead of being invented.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel
from career_copilot.core.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class ResumeRewriteInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume — the sole source of fact")
    jd_text: Optional[str] = Field(default=None, description="Target job description, if available, used to tailor emphasis and keywords")
    target_role: Optional[str] = Field(default=None, description="Target role title, used for context if no JD is supplied")
    company_name: Optional[str] = Field(default=None, description="Target company name, used to inform startup-vs-enterprise tone if no JD is supplied")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ResumeVersionKind(str, Enum):
    ATS = "ats"
    RECRUITER = "recruiter"
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    EXECUTIVE = "executive"


class ResumeVersion(BaseModel):
    version: ResumeVersionKind
    applicable: bool = Field(
        default=True, description="False only for the executive version when the candidate's level doesn't warrant one"
    )
    skip_reason: Optional[str] = Field(default=None, description="Required and specific if applicable is False")
    tailored_for: str = Field(..., description="What this version optimizes for and why")
    formatting_notes: str = Field(..., description="How this version's formatting differs, e.g. single-column and keyword-forward for ATS")
    key_changes: List[str] = Field(
        default_factory=list, description="What's different from the base facts for this version — tone/ordering/emphasis only, never new facts"
    )
    full_text: str = Field(default="", description="Complete, ready-to-use rewritten resume text for this version; empty if not applicable")


class UnmetImprovementOpportunity(BaseModel):
    location: str = Field(..., description="Which bullet/section this applies to")
    reason_not_improved: str = Field(..., description="Why it couldn't be strengthened without fabricating, e.g. no metric stated anywhere in the source")


class ResumeRewriteOutput(BaseModel):
    candidate_name: Optional[str] = None
    target_role: Optional[str] = None
    versions: List[ResumeVersion] = Field(default_factory=list, description="Always 5 entries: ats, recruiter, startup, enterprise, executive")
    global_changes_summary: List[str] = Field(
        default_factory=list, description="Changes applied across all versions, e.g. weak verbs replaced, redundant content trimmed"
    )
    unmet_improvement_opportunities: List[UnmetImprovementOpportunity] = Field(default_factory=list)
    human_readable_summary: str = Field(..., description="Markdown summary of this rewrite for a human reader")
    rewrite_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Resume Rewrite Agent inside the AI Career Copilot, a multi-agent \
system. You act as an executive resume writer who has rewritten resumes \
across every seniority level and company stage.

Your sole job is to rewrite the given resume into multiple audience-tailored \
versions. You are NOT analyzing gaps against a JD, NOT scoring ATS \
compatibility, and NOT giving career advice — those are other agents' jobs. \
Stay in your lane.

Non-negotiable rules:
1. The source resume text is the ONLY source of fact. No version may add an \
employer, title, date, metric, scope (team size, budget, user count), or \
achievement that is not stated or directly implied in the source. \
Rephrasing, reordering, and strengthening language is expected; inventing \
facts is not.
2. Where a bullet would be materially stronger with a metric or specifics \
the source doesn't provide, do NOT invent one — leave it qualitative and \
record it in `unmet_improvement_opportunities` instead.
3. Every version must use strong action verbs, lead with business impact, \
include metrics only where the source supports them, keep bullets concise \
(roughly one line each), and use consistent formatting throughout that \
version.
4. Generate exactly 5 versions in this order: ats, recruiter, startup, \
enterprise, executive. The first four are always `applicable: true`. Mark \
`executive` as `applicable: false` with a specific `skip_reason` if the \
candidate's demonstrated scope (titles, scope of ownership, people \
leadership) doesn't support an executive-tier framing — do not inflate \
scope to justify generating one anyway.
5. Tailor each applicable version distinctly, not just with a different \
label on the same content:
   - ats: single-column structure described in `formatting_notes`, standard \
section headings, keyword-forward phrasing aligned to the JD if supplied, \
minimal styling cues.
   - recruiter: optimized for a ~30-second scan — strongest achievements \
surfaced first, punchy and concrete.
   - startup: emphasizes ownership, breadth, speed, and comfort with \
ambiguity — pulls forward evidence of ownership and generalist range.
   - enterprise: emphasizes process rigor, cross-functional stakeholder \
management, scale, and structured execution.
   - executive (if applicable): emphasizes strategic/org-level impact and \
business outcomes over day-to-day task descriptions.
6. `full_text` for each applicable version must be a complete, ready-to-use \
resume (contact line, summary, experience with bullets, skills, education) \
— not a fragment or a diff.
7. Set `rewrite_confidence` based on how much the source resume text \
supported strong rewrites without needing invention, not on how impressive \
the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class ResumeRewriteAgent(BaseAgent[ResumeRewriteInput, ResumeRewriteOutput]):
    name = "Resume Rewrite Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = ResumeRewriteInput
    output_model = ResumeRewriteOutput

    def __init__(self, client: Optional[LLMClient] = None):
        # Five full resume versions in one structured response need more headroom
        # than the 8192-token default other agents use.
        super().__init__(client or LLMClient(max_tokens=16384))

    def build_user_prompt(self, data: ResumeRewriteInput) -> str:
        context = ""
        if data.jd_text:
            context += f"--- TARGET JOB DESCRIPTION START ---\n{data.jd_text}\n--- TARGET JOB DESCRIPTION END ---\n\n"
        elif data.target_role or data.company_name:
            hints = []
            if data.target_role:
                hints.append(f"target role: {data.target_role}")
            if data.company_name:
                hints.append(f"target company: {data.company_name}")
            context += f"Context (no JD supplied): {', '.join(hints)}\n\n"

        return (
            "Rewrite the following resume into 5 tailored versions per your instructions.\n\n"
            f"{context}"
            "--- SOURCE RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- SOURCE RESUME TEXT END ---"
        )
