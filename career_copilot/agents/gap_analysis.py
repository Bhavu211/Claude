"""Agent 6: Gap Analysis Agent.

Compares a resume against a job description, requirement by requirement.
This agent's one hard rule is the strictest in the system: never claim a
requirement is met without quotable evidence. A requirement can be YES
(clearly met with direct evidence), PARTIAL (related evidence exists but
doesn't fully cover it), or NO (nothing supports it) — there is no
"probably fine" option.

Gap severity is distinct from the JD's own priority: a JD-critical
requirement that's fully met has no gap at all (severity NONE), while a
JD-critical requirement with zero evidence is the worst case (severity
CRITICAL). Severity answers "how much does this specific shortfall matter
for this specific application," not "how important is this skill in
general."
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, RequirementPriority

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class GapAnalysisInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume")
    jd_text: str = Field(..., description="Full plain-text content of the target job description")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class PresenceStatus(str, Enum):
    YES = "yes"
    PARTIAL = "partial"
    NO = "no"


class GapSeverity(str, Enum):
    NONE = "none"  # fully met — not actually a gap
    OPTIONAL = "optional"
    IMPORTANT = "important"
    CRITICAL = "critical"


class GapAnalysisRow(BaseModel):
    requirement: str = Field(..., description="The JD requirement being assessed, normalized to a short phrase")
    jd_priority: Optional[RequirementPriority] = Field(default=None, description="Priority this requirement carries in the JD")
    present_in_resume: PresenceStatus
    supporting_evidence: Optional[str] = Field(
        default=None, description="Verbatim or close paraphrase from the resume; must be null/omitted when present_in_resume is 'no'"
    )
    gap_severity: GapSeverity
    recommendation: str = Field(
        ..., description="Concrete next step; must distinguish a resume-optimization fix from a genuine experience gap that rewriting cannot close"
    )


class GapAnalysisOutput(BaseModel):
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    rows: List[GapAnalysisRow] = Field(default_factory=list, description="One row per distinct JD requirement")

    strongest_matches: List[str] = Field(default_factory=list, description="Best-evidenced, highest-confidence matches")
    critical_gaps: List[str] = Field(default_factory=list, description="Requirement names with gap_severity == critical, for quick reference")
    overall_fit_assessment: str = Field(..., description="Narrative synthesis of the gap pattern as a whole")

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    analysis_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Gap Analysis Agent inside the AI Career Copilot, a multi-agent \
system. You act as a rigorous hiring analyst whose entire job is comparing \
a resume against a job description, requirement by requirement, with zero \
tolerance for unsupported claims.

Your sole job is this comparison. You are NOT rewriting the resume, NOT \
scoring ATS compatibility, and NOT giving career advice — those are other \
agents' jobs. Stay in your lane.

Non-negotiable rules:
1. Build one row per distinct requirement drawn from the JD — explicit \
Requirements/Preferred/Nice-to-have sections and clearly stated \
responsibilities/KPIs that imply a needed skill or experience.
2. NEVER mark `present_in_resume` as "yes" without quotable \
`supporting_evidence` from the resume text. Use "partial" when related but \
incomplete evidence exists (e.g. one of two named regulations is mentioned, \
or a skill is listed but never demonstrated in a bullet) — explain the gap \
between what's claimed and what's evidenced in the recommendation. Use "no" \
and leave `supporting_evidence` empty when nothing in the resume supports \
the requirement, even loosely.
3. `gap_severity` reflects how much THIS shortfall matters for THIS \
application — not general skill importance. A fully-met requirement is \
`none` regardless of how critical the JD makes it. A requirement with zero \
evidence gets a severity that reflects both the JD's own priority for it \
and how central it seems to the role.
4. Every `recommendation` must distinguish two different situations: (a) a \
resume-optimization fix (the experience likely exists but isn't written \
down — say what to add) versus (b) a genuine experience gap that no amount \
of rewriting can close (say so plainly, and suggest how the candidate might \
address it in the interview process or via a portfolio project instead of \
implying the resume should paper over it).
5. `overall_fit_assessment` and `strongest_matches` must be grounded in the \
`rows` you produced — don't state a fit conclusion the row-level evidence \
doesn't support.
6. Set `analysis_confidence` based on how clearly the JD's requirements and \
the resume's content could be matched, not on how strong the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class GapAnalysisAgent(BaseAgent[GapAnalysisInput, GapAnalysisOutput]):
    name = "Gap Analysis Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = GapAnalysisInput
    output_model = GapAnalysisOutput

    def build_user_prompt(self, data: GapAnalysisInput) -> str:
        return (
            "Compare the following resume against the job description per your instructions. "
            "Produce one row per distinct JD requirement.\n\n"
            "--- JOB DESCRIPTION TEXT START ---\n"
            f"{data.jd_text}\n"
            "--- JOB DESCRIPTION TEXT END ---\n\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---"
        )
