"""Agent 2: JD Intelligence Agent.

Acts as a talent acquisition specialist decoding what a job description
actually asks for. Downstream agents (Gap Analysis, Skill Evidence, ATS
Optimization, Resume Rewrite) treat this agent's `requirements` list as the
target to measure the candidate against — so precision on priority
(critical/important/nice-to-have) matters as much as coverage.
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


class JDIntelligenceInput(BaseModel):
    jd_text: str = Field(..., description="Full plain-text content of the job description")
    company_name: Optional[str] = Field(default=None, description="Company name if known separately from the JD text")
    role_title: Optional[str] = Field(default=None, description="Role title if known separately from the JD text")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class RequirementType(str, Enum):
    SKILL = "skill"
    TOOL = "tool"
    TECHNOLOGY = "technology"
    CERTIFICATION = "certification"
    DOMAIN_EXPERTISE = "domain_expertise"
    LEADERSHIP = "leadership"
    PRODUCT = "product"
    EXPERIENCE = "experience"


class ClassifiedRequirement(BaseModel):
    requirement: str = Field(..., description="The requirement, normalized to a short phrase")
    type: RequirementType
    priority: RequirementPriority
    evidence_text: str = Field(..., description="Verbatim or close paraphrase from the JD supporting this requirement")
    reasoning: str = Field(..., description="Why this was classified at this priority, e.g. language used ('must have' vs 'a plus')")


class HiddenExpectation(BaseModel):
    expectation: str = Field(..., description="An expectation not explicitly stated as a requirement but implied by the JD's language")
    signal_text: str = Field(..., description="The JD phrase(s) that imply this expectation")
    confidence: ConfidenceLevel


class JDIntelligenceOutput(BaseModel):
    # --- Extracted structure -------------------------------------------------
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    seniority_level: Optional[str] = Field(default=None, description="e.g. 'Associate', 'Senior', 'Lead', 'Director' — as stated or clearly implied by title")
    years_of_experience_required: Optional[str] = Field(default=None, description="As stated in the JD, e.g. '5+ years'")
    requirements: List[ClassifiedRequirement] = Field(
        default_factory=list, description="Every skill, tool, technology, certification, domain, leadership, and product requirement found, each classified by priority"
    )
    responsibilities: List[str] = Field(default_factory=list, description="Day-to-day responsibilities as stated")
    kpis: List[str] = Field(default_factory=list, description="Explicit or clearly implied success metrics for the role")
    hidden_expectations: List[HiddenExpectation] = Field(
        default_factory=list, description="Expectations implied by tone/phrasing but not listed as explicit requirements"
    )

    # --- Intelligence layer ---------------------------------------------------
    recruiter_intent: str = Field(..., description="Narrative synthesis of what the hiring team is actually optimizing for")
    hiring_priorities: List[str] = Field(default_factory=list, description="Ranked list (highest first) of what matters most for this hire")

    # --- Meta ---------------------------------------------------------------
    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    analysis_confidence: ConfidenceLevel
    limitations: List[str] = Field(
        default_factory=list, description="Explicit statement of anything that could not be determined from the JD alone"
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the JD Intelligence Agent inside the AI Career Copilot, a multi-agent \
system. You act as a talent acquisition specialist who has written and \
triaged hundreds of job descriptions and knows how to read between the lines \
of one.

Your sole job is to decode a job description into structured, prioritized \
requirements and recruiter intent. You are NOT looking at any resume, NOT \
scoring a candidate, and NOT making hiring recommendations — those are \
other agents' jobs. Stay in your lane.

Non-negotiable rules:
1. Every item in `requirements` must be traceable to specific JD text in \
`evidence_text` — do not invent requirements the JD does not state or \
strongly imply.
2. Classify priority using the JD's own language as the primary signal: \
"must have" / "required" / listed under a "Requirements" heading -> critical; \
"preferred" / "strongly desired" / listed under "Preferred Qualifications" -> \
important; "nice to have" / "a plus" / "bonus" -> nice_to_have. When the JD \
gives no explicit signal, use reasoned judgment and say so in `reasoning`.
3. `hidden_expectations` must be clearly inferable from specific phrasing \
(e.g. "fast-paced, ambiguous environment" implies high autonomy expected) — \
cite the exact `signal_text` and mark `confidence` honestly. Do not pad this \
list with generic guesses.
4. `recruiter_intent` and `hiring_priorities` should synthesize the JD as a \
whole — what is this hire actually for, and what would make a hiring \
manager say yes — grounded in what's written, not speculation about the \
company beyond this document.
5. If the JD is vague, incomplete, or contradictory in a way that limits your \
analysis, say so explicitly in `limitations` instead of silently filling gaps.
6. Set `analysis_confidence` based on how complete and unambiguous the JD \
text was, not on how attractive the role is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class JDIntelligenceAgent(BaseAgent[JDIntelligenceInput, JDIntelligenceOutput]):
    name = "JD Intelligence Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = JDIntelligenceInput
    output_model = JDIntelligenceOutput

    def build_user_prompt(self, data: JDIntelligenceInput) -> str:
        hints = ""
        if data.company_name:
            hints += f"\nKnown company name (use if JD doesn't state one): {data.company_name}\n"
        if data.role_title:
            hints += f"\nKnown role title (use if JD doesn't state one): {data.role_title}\n"
        return (
            "Analyze the following job description. Extract structured, "
            "prioritized requirements and recruiter intent per your instructions.\n"
            f"{hints}\n"
            "--- JOB DESCRIPTION TEXT START ---\n"
            f"{data.jd_text}\n"
            "--- JOB DESCRIPTION TEXT END ---"
        )
