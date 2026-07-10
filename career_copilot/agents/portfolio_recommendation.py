"""Agent 8: Portfolio Recommendation Agent.

Designs portfolio projects that close experience gaps. Unlike the extraction
agents (Resume Analysis, JD Intelligence, ...), this agent doesn't re-read
the resume or JD — it's a pure synthesis step that takes a already-identified
list of gaps (typically sourced from Gap Analysis Agent and/or Skill
Evidence Agent) and designs buildable projects to close them.

Not every gap is portfolio-shaped. People-management/mentoring experience
and credentials (certifications) can't be credibly simulated by a solo
project — this agent must say so in `gaps_not_addressed` rather than force
a contrived project onto a gap that needs a different kind of fix.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class PortfolioRecommendationInput(BaseModel):
    target_role: str = Field(..., description="Target role title")
    company_name: Optional[str] = Field(default=None, description="Target company, for domain-relevant project framing")
    gaps_to_close: List[str] = Field(
        ..., description="Specific gaps or weakly-evidenced skills to design projects around, typically sourced from Gap Analysis / Skill Evidence Agent output"
    )
    candidate_background: Optional[str] = Field(
        default=None, description="Brief context on the candidate's existing skills/domain/tech stack so projects build on strengths rather than starting from zero"
    )
    max_projects: int = Field(default=3, ge=1, le=5, description="Maximum number of projects to propose")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class PortfolioProject(BaseModel):
    title: str
    addresses_gaps: List[str] = Field(..., description="Which of the input gaps_to_close this project is designed to close")
    business_problem: str
    target_users: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    ai_opportunities: List[str] = Field(default_factory=list, description="Empty if AI isn't a natural fit — don't force it in")
    apis: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)
    prd_outline: List[str] = Field(..., description="Section-by-section outline of a one-page PRD for this project")
    mvp: str = Field(..., description="The smallest version that's still worth showing in an interview")
    future_enhancements: List[str] = Field(default_factory=list)
    estimated_build_time: Optional[str] = None
    priority_rank: int = Field(..., ge=1, description="1 = highest priority")
    priority_reasoning: str = Field(..., description="Why this rank, tied to gap severity and build effort")


class PortfolioRecommendationOutput(BaseModel):
    target_role: str
    company_name: Optional[str] = None
    projects: List[PortfolioProject] = Field(default_factory=list, description="Ordered by priority_rank")
    gaps_not_addressed: List[str] = Field(
        default_factory=list, description="Input gaps no project addresses, with why — e.g. experience or credential gaps a solo project can't simulate"
    )
    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    recommendation_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Portfolio Recommendation Agent inside the AI Career Copilot, a \
multi-agent system. You act as a product leader who designs small, buildable \
portfolio projects that give a candidate real, demonstrable proof for a \
specific gap — not generic "build a to-do app" advice.

Your sole job is designing projects against the gaps you're given. You do \
NOT re-analyze the resume or JD, NOT judge overall candidacy — those are \
other agents' jobs (Gap Analysis and Skill Evidence already did that work; \
trust the `gaps_to_close` list you're handed). Stay in your lane.

Non-negotiable rules:
1. Only design projects for gaps that a solo portfolio project can \
credibly close — skill/tool/technique gaps and thin evidence are \
portfolio-shaped. People-management/mentoring experience and credentials \
(certifications) are NOT — a solo project cannot simulate managing another \
person or substitute for enrolling in a certification. Put these in \
`gaps_not_addressed` with a specific reason instead of forcing a contrived \
project onto them.
2. Every project must tie back to specific gaps in `addresses_gaps` — don't \
propose a generically impressive project that doesn't map to anything in \
`gaps_to_close`.
3. Ground projects in the candidate's actual domain (use `candidate_background` \
and the target role/company) rather than generic examples — a fraud/risk PM \
candidate should get fraud/risk-flavored projects, not an unrelated todo app.
4. `ai_opportunities` must be a genuine fit for that specific project, not a \
reflexive "add AI" — leave it empty if there's no natural opportunity.
5. `prd_outline` and `mvp` must describe something buildable in the stated \
`estimated_build_time` by one person — no project should implicitly require \
a team.
6. Rank projects by `priority_rank`, reasoning about gap severity (from the \
input) and build effort together, not just build effort alone.
7. Set `recommendation_confidence` based on how clearly the input gaps \
could be translated into buildable projects, not on how ambitious the \
projects are.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class PortfolioRecommendationAgent(BaseAgent[PortfolioRecommendationInput, PortfolioRecommendationOutput]):
    name = "Portfolio Recommendation Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = PortfolioRecommendationInput
    output_model = PortfolioRecommendationOutput

    def build_user_prompt(self, data: PortfolioRecommendationInput) -> str:
        company_hint = f" at {data.company_name}" if data.company_name else ""
        background = f"\nCandidate background: {data.candidate_background}\n" if data.candidate_background else ""
        gaps_block = "\n".join(f"- {g}" for g in data.gaps_to_close)
        return (
            f"Design up to {data.max_projects} portfolio project(s) for a candidate targeting "
            f"'{data.target_role}'{company_hint}, per your instructions.\n"
            f"{background}\n"
            "Gaps to close:\n"
            f"{gaps_block}"
        )
