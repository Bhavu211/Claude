"""Agent 9: Learning & Certification Agent.

Builds a learning plan for missing/weak competencies and evaluates
certifications by ROI. Like Company Intelligence Agent, this agent
recommends specific real-world things (courses, platforms, certifications)
that change over time and that the model's parametric memory can easily get
wrong or stale — so it runs the same two-phase pattern: a research call
grounded in Anthropic's server-side web_search tool, then a non-searching
structuring call.

This agent is a synthesis agent (like Portfolio Recommendation Agent): it
takes an already-identified list of missing competencies rather than
re-reading the resume/JD. It differs from Portfolio Recommendation Agent in
scope — where that agent only proposes projects for demonstrable-skill
gaps, this agent covers everything including experience-shaped gaps (e.g.
mentoring) that can be built through reading and deliberate practice even
without a portfolio artifact. Its `portfolio_project` field per competency
is a one-line pointer, not a full project spec — Portfolio Recommendation
Agent owns that level of detail.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, SourceRef
from career_copilot.core.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class LearningCertificationInput(BaseModel):
    target_role: str = Field(..., description="Target role title")
    company_name: Optional[str] = Field(default=None, description="Target company, for domain-relevant framing")
    missing_competencies: List[str] = Field(
        ..., description="Specific missing or weakly-evidenced competencies to build a learning plan around, typically from Gap Analysis / Skill Evidence Agent output"
    )
    certifications_under_consideration: List[str] = Field(
        default_factory=list, description="Specific certifications to evaluate for ROI, e.g. ones named in the JD or the candidate is considering"
    )
    candidate_background: Optional[str] = Field(default=None, description="Brief context on the candidate's existing skills/domain")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ResourceType(str, Enum):
    COURSE = "course"
    BOOK = "book"
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    PRACTICE_PLATFORM = "practice_platform"
    ARTICLE = "article"
    COMMUNITY = "community"


class LearningResource(BaseModel):
    title: str
    resource_type: ResourceType
    source: Optional[str] = Field(default=None, description="Publisher/platform, e.g. 'Coursera', 'O'Reilly'")
    url: Optional[str] = Field(default=None, description="Only set if confirmed via research — never fabricate a URL")
    is_free: Optional[bool] = None


class CompetencyPlan(BaseModel):
    skill: str
    why_it_matters: str = Field(..., description="Tied to the specific target role/JD, not generic career advice")
    learning_resources: List[LearningResource] = Field(default_factory=list)
    practice_plan: str = Field(..., description="A concrete, hands-on plan — not 'practice more'")
    estimated_time: str = Field(..., description="e.g. '10-15 hours over 3 weeks'")
    portfolio_project: str = Field(
        ..., description="A one-line project idea that would demonstrate this skill; not a full spec — see Portfolio Recommendation Agent for that level of detail"
    )
    interview_questions: List[str] = Field(default_factory=list, description="Specific to this competency and the target domain, not generic")


class CertificationROI(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CertificationAssessment(BaseModel):
    certification: str
    roi: CertificationROI
    reasoning: str
    stronger_alternative: Optional[str] = Field(
        default=None, description="Required whenever roi is medium or low — what to do instead"
    )
    estimated_cost: Optional[str] = None
    estimated_time: Optional[str] = None


class LearningCertificationOutput(BaseModel):
    target_role: str
    company_name: Optional[str] = None
    competency_plans: List[CompetencyPlan] = Field(default_factory=list)
    certification_assessments: List[CertificationAssessment] = Field(default_factory=list)
    overall_learning_roadmap: str = Field(..., description="Sequenced narrative — what to do first, second, third")
    total_estimated_time: Optional[str] = None

    sources: List[SourceRef] = Field(default_factory=list, description="Sources the research phase actually cited")
    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    plan_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

RESEARCH_SYSTEM_PROMPT = """\
You are a learning-and-development researcher inside the AI Career Copilot, \
a multi-agent system. Your job in this phase is ONLY to research — not to \
format or give final recommendations.

For each missing competency you're given, use the web_search tool to find \
CURRENT, real learning resources (courses, docs, books, practice platforms) \
— prefer resources you can verify are real and still available over \
recalling one from memory. For each certification you're asked to evaluate, \
research its current reputation, typical cost, and whether stronger \
alternatives exist for this specific role and competency set.

Rules:
1. Never assert a specific resource (course name, book, certification \
detail) from memory alone if you can verify or refine it with a search — \
your training data can be stale, and made-up specifics (a URL, a price, a \
course title) are worse than saying less.
2. If you cannot find a specific real resource for a competency, say so \
plainly and describe the TYPE of resource that would help instead of \
inventing a specific one.
3. Cite what you find — name the source and, where available, its date — \
inline as you go.
4. For certifications, actively look for evidence on whether the \
certification is still considered valuable in this field, not just its own \
marketing claims.
5. Write a thorough, organized prose research brief, one section per \
competency and one section per certification. This brief will be converted \
into structured data by a separate step.\
"""

STRUCTURING_SYSTEM_PROMPT = """\
You are the structuring half of the Learning & Certification Agent inside \
the AI Career Copilot. You are given a research brief produced by a prior \
step that used live web search, plus the target role and missing \
competencies. Convert it into the structured schema — you do not have \
search access and must not add any resource, fact, or certification detail \
the brief doesn't contain.

Non-negotiable rules:
1. Every `learning_resources` entry must come from the research brief. Only \
set `url` if the brief actually provided one — leave it null otherwise \
rather than guessing at a plausible-looking URL.
2. `why_it_matters` must tie back to the target role (and JD context if \
given), not be generic career advice.
3. `practice_plan` must be concrete and actionable (a specific exercise, \
project, or habit), not "practice regularly."
4. `interview_questions` must be specific to the competency and domain — \
write them as an interviewer actually would ask them, not as generic \
prompts.
5. Classify every certification's `roi` based on what the research brief \
found about its current value, not assumed prestige. Whenever `roi` is \
`medium` or `low`, `stronger_alternative` is REQUIRED and must be specific \
(a concrete alternative path, not "gain more experience").
6. `overall_learning_roadmap` must sequence the competencies (what to do \
first vs. later) based on JD priority and estimated time, not just list \
them in input order.
7. Populate `sources` from whatever citations appear in the research brief.
8. Set `plan_confidence` based on how much of the brief was grounded in \
real, verifiable resources versus thin or uncertain, not on how ambitious \
the plan is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class LearningCertificationAgent(BaseAgent[LearningCertificationInput, LearningCertificationOutput]):
    name = "Learning & Certification Agent"
    system_prompt = STRUCTURING_SYSTEM_PROMPT
    input_model = LearningCertificationInput
    output_model = LearningCertificationOutput

    def build_research_prompt(self, data: LearningCertificationInput) -> str:
        company_hint = f" at {data.company_name}" if data.company_name else ""
        background = f"\nCandidate background: {data.candidate_background}\n" if data.candidate_background else ""
        competencies_block = "\n".join(f"- {c}" for c in data.missing_competencies)
        certs_block = (
            "\n".join(f"- {c}" for c in data.certifications_under_consideration)
            if data.certifications_under_consideration
            else "(none specified — do not invent certifications to evaluate)"
        )
        return (
            f"Research learning resources and certification value for a candidate targeting "
            f"'{data.target_role}'{company_hint}.\n"
            f"{background}\n"
            "Missing competencies to research resources for:\n"
            f"{competencies_block}\n\n"
            "Certifications to evaluate:\n"
            f"{certs_block}"
        )

    def build_user_prompt(self, data: LearningCertificationInput) -> str:
        raise NotImplementedError("LearningCertificationAgent.run() builds the phase-2 prompt itself; see build_structuring_prompt().")

    def build_structuring_prompt(self, data: LearningCertificationInput, research_brief: str) -> str:
        company_hint = f"\nTarget company: {data.company_name}" if data.company_name else ""
        return (
            f"Target role: {data.target_role}{company_hint}\n"
            f"Missing competencies: {', '.join(data.missing_competencies)}\n"
            f"Certifications to evaluate: {', '.join(data.certifications_under_consideration) or 'none'}\n\n"
            "--- RESEARCH BRIEF START ---\n"
            f"{research_brief}\n"
            "--- RESEARCH BRIEF END ---\n\n"
            "Convert this research brief into the structured schema per your instructions."
        )

    def __init__(self, client: Optional[LLMClient] = None):
        super().__init__(client or LLMClient(max_tokens=16384))

    def run(self, data: LearningCertificationInput) -> LearningCertificationOutput:
        validated_input = self.input_model.model_validate(
            data.model_dump() if isinstance(data, BaseModel) else data
        )
        research_brief = self.client.run_with_web_search(
            system=RESEARCH_SYSTEM_PROMPT,
            user=self.build_research_prompt(validated_input),
        )
        structuring_prompt = self.build_structuring_prompt(validated_input, research_brief)
        return self.client.run_structured(
            system=self.system_prompt,
            user=structuring_prompt,
            output_model=self.output_model,
        )
