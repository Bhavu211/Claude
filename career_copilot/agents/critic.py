"""Agent 17: Critic Agent.

Reviews and validates every other content agent's output before it reaches
the user. This agent creates no new career content — its only job is
finding real problems (factual inaccuracy, unsupported claims, logical
inconsistency, low-value recommendations) and scoring what it reviews
honestly, including scoring something highly when it genuinely deserves it.

A critic that finds nothing wrong in 15 outputs is a critic that isn't
looking hard enough — this agent is explicitly instructed to check
internal arithmetic and cross-field consistency (do stated totals actually
match what they're totaling?), not just re-read prose for a vibe check.

Like Planner Agent, this agent grounds itself in the real `AGENT_REGISTRY`
so it reviews only agents that actually exist, under their real names.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, Severity
from career_copilot.core.llm_client import LLMClient
from career_copilot.core.registry import AGENT_REGISTRY

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class CriticInput(BaseModel):
    resume_text: str = Field(..., description="Ground truth for fact-checking claims made across all reviewed outputs")
    jd_text: Optional[str] = None
    company_name: Optional[str] = None

    # Prefer the full JSON output per agent (as a string) for deeper fact-
    # checking; a human_readable_summary alone limits review depth to what
    # that agent chose to highlight in prose.
    resume_analysis_output: Optional[str] = None
    jd_intelligence_output: Optional[str] = None
    company_intelligence_output: Optional[str] = None
    ats_optimization_output: Optional[str] = None
    resume_rewrite_output: Optional[str] = None
    gap_analysis_output: Optional[str] = None
    skill_evidence_output: Optional[str] = None
    portfolio_recommendation_output: Optional[str] = None
    learning_certification_output: Optional[str] = None
    recruiter_simulation_output: Optional[str] = None
    interview_coach_output: Optional[str] = None
    linkedin_optimization_output: Optional[str] = None
    application_assets_output: Optional[str] = None
    career_strategy_output: Optional[str] = None
    final_report_output: Optional[str] = None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_MINOR_REVISIONS = "approved_with_minor_revisions"
    REQUIRES_MAJOR_REVISIONS = "requires_major_revisions"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScoreDimensions(BaseModel):
    accuracy: int = Field(..., ge=0, le=100)
    authenticity: int = Field(..., ge=0, le=100)
    ats_readiness: int = Field(..., ge=0, le=100)
    recruiter_readability: int = Field(..., ge=0, le=100)
    completeness: int = Field(..., ge=0, le=100)
    evidence_quality: int = Field(..., ge=0, le=100)
    company_alignment: int = Field(..., ge=0, le=100)
    career_impact: int = Field(..., ge=0, le=100)
    consistency: int = Field(..., ge=0, le=100)
    actionability: int = Field(..., ge=0, le=100)


class CriticIssue(BaseModel):
    issue: str
    severity: Severity
    location: str = Field(..., description="Which field/section of the reviewed agent's output this is in")
    recommended_fix: str


class AgentReview(BaseModel):
    agent_id: str = Field(..., description="Must match an id in AGENT_REGISTRY")
    scores: ScoreDimensions
    overall_score: int = Field(..., ge=0, le=100, description="Not necessarily a plain average — weight what matters most for this agent's job")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    issues_found: List[CriticIssue] = Field(default_factory=list, description="Empty is fine if the output genuinely has no issues — don't invent one")
    approval_status: ApprovalStatus
    review_reasoning: str = Field(..., description="Why this score/status, referencing specific evidence, not a generic statement")


class FinalVerdict(BaseModel):
    overall_system_quality_score: int = Field(..., ge=0, le=100)
    critical_issues_count: int
    major_issues_count: int
    minor_issues_count: int
    hallucination_risk: RiskLevel
    confidence_level: ConfidenceLevel
    final_recommendation: str


class CriticOutput(BaseModel):
    agent_reviews: List[AgentReview] = Field(..., description="One entry per reviewed agent")
    final_verdict: FinalVerdict
    human_readable_summary: str = Field(..., description="Markdown summary of this review for a human reader")
    review_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

_REVIEWABLE_AGENT_IDS = [spec.id for spec in AGENT_REGISTRY if spec.id != "planner"]

SYSTEM_PROMPT = f"""\
You are the Critic Agent inside the AI Career Copilot, a multi-agent \
system. You review every other content agent's output before it reaches \
the user. You create no new career content — you find real problems and \
score honestly, including scoring something highly when it genuinely \
deserves it.

You may only review agents that exist in this list (their real ids): \
{_REVIEWABLE_AGENT_IDS}. Never invent an agent or review one not in this \
list.

Non-negotiable rules:
1. Check FACTS, not just prose quality. For every reviewed output, verify \
claims against the resume/JD text you were given where possible, and check \
INTERNAL arithmetic/cross-field consistency — e.g. does a stated total \
actually match what it's supposedly totaling, do counts in a summary match \
counts in the structured data, does one agent's conclusion contradict \
another's. A critic that only re-reads prose for tone is not doing this \
job.
2. `issues_found` must be empty for an agent if you genuinely found \
nothing wrong — do not invent an issue to seem thorough, and do not skip a \
real issue to seem generous. Both failure modes defeat the point of this \
agent.
3. Score `authenticity` by checking for AI-generated tells (buzzword \
overload, generic statements, repetitive structure) — a resume rewrite \
that reads well AND stays grounded in real resume facts should score high \
on both `accuracy` and `authenticity`.
4. Score `consistency` partly by checking cross-agent agreement — if \
multiple agents independently flag the same finding, that's a positive \
consistency signal, not noise; if two agents' outputs contradict each \
other (e.g. one implies more experience than another), that's a real \
issue and belongs in `issues_found` with severity reflecting how \
consequential the contradiction is.
5. `approval_status` must follow from the actual issues found: \
`rejected` only for something with a critical, fabrication-level problem; \
`requires_major_revisions` for a major factual or consistency error; \
`approved_with_minor_revisions` for minor/suggestion-only issues; \
`approved` only when there's genuinely nothing worth flagging.
6. `final_verdict.hallucination_risk` should reflect what you actually \
found across all reviews — if every agent's claims traced cleanly to real \
source material, say `low` and say why, don't hedge upward by default.
7. Set `review_confidence` based on how much material (full JSON vs. only \
a summary) you had for each agent, noting in `limitations` where review \
depth was limited by what you were given.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class CriticAgent(BaseAgent[CriticInput, CriticOutput]):
    name = "Critic Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = CriticInput
    output_model = CriticOutput

    def __init__(self, client: Optional[LLMClient] = None):
        super().__init__(client or LLMClient(max_tokens=16384))

    def build_user_prompt(self, data: CriticInput) -> str:
        outputs = [
            ("resume_analysis", data.resume_analysis_output),
            ("jd_intelligence", data.jd_intelligence_output),
            ("company_intelligence", data.company_intelligence_output),
            ("ats_optimization", data.ats_optimization_output),
            ("resume_rewrite", data.resume_rewrite_output),
            ("gap_analysis", data.gap_analysis_output),
            ("skill_evidence", data.skill_evidence_output),
            ("portfolio_recommendation", data.portfolio_recommendation_output),
            ("learning_certification", data.learning_certification_output),
            ("recruiter_simulation", data.recruiter_simulation_output),
            ("interview_coach", data.interview_coach_output),
            ("linkedin_optimization", data.linkedin_optimization_output),
            ("application_assets", data.application_assets_output),
            ("career_strategy", data.career_strategy_output),
            ("final_report", data.final_report_output),
        ]
        outputs_block = "\n\n".join(
            f"--- {agent_id} OUTPUT START ---\n{output}\n--- {agent_id} OUTPUT END ---"
            for agent_id, output in outputs
            if output
        )
        missing = [agent_id for agent_id, output in outputs if not output]
        missing_note = f"\n\nNo output provided for: {', '.join(missing)} — do not review these." if missing else ""

        context = f"Resume:\n{data.resume_text}\n"
        if data.jd_text:
            context += f"\nJob Description:\n{data.jd_text}\n"
        if data.company_name:
            context += f"\nTarget company: {data.company_name}\n"

        return (
            "Review the following agent outputs per your instructions. Use the resume/JD as ground truth "
            "for fact-checking.\n\n"
            f"--- GROUND TRUTH START ---\n{context}--- GROUND TRUTH END ---\n\n"
            f"{outputs_block}"
            f"{missing_note}"
        )
