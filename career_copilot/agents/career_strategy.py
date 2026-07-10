"""Agent 14: Career Strategy Agent.

Advises on long-term career positioning: role fit, market salary, seniority
evaluation, promotion readiness, ranked career risks/opportunities, and a
30-day / 90-day / 1-year action plan.

Like Company Intelligence and Learning & Certification Agents, this agent
runs a research phase before structuring — market salary data is a real,
current, external fact that goes stale and varies widely by source, so
guessing a number from parametric memory would be exactly the kind of
fabrication risk this system is built to avoid. Role fit, seniority, and
promotion readiness are reasoning over the resume plus condensed upstream
findings, not external facts, so those stay in the structuring phase.

This is a synthesis agent: it takes resume_text (sole fact source) plus a
condensed summary of what Gap Analysis / Skill Evidence / Recruiter
Simulation Agents already found, rather than re-deriving fit from scratch a
fourth time.
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


class CareerStrategyInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume — the sole source of fact")
    target_role: str = Field(..., description="Target role title")
    company_name: Optional[str] = Field(default=None, description="Target company, if any")
    location: Optional[str] = Field(default=None, description="e.g. 'Bengaluru, India' — used for market salary research")
    key_findings_summary: Optional[str] = Field(
        default=None, description="Condensed findings from Gap Analysis / Skill Evidence / Recruiter Simulation Agents, so this agent doesn't re-derive fit from scratch"
    )
    portfolio_and_learning_plan_summary: Optional[str] = Field(
        default=None, description="Condensed summary of Portfolio Recommendation / Learning & Certification Agent outputs, to inform the action plans"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class FitLevel(str, Enum):
    STRONG_FIT = "strong_fit"
    GOOD_FIT_WITH_GAPS = "good_fit_with_gaps"
    STRETCH = "stretch"
    MISMATCH = "mismatch"


class ImpactLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SalaryEstimate(BaseModel):
    range_low: str = Field(..., description="e.g. '₹42,00,000'")
    range_high: str = Field(..., description="e.g. '₹65,00,000'")
    currency_and_period: str = Field(..., description="e.g. 'INR per year, total compensation'")
    reasoning: str = Field(..., description="Must cite what the estimate is anchored on and note disagreement across sources if any")


class RankedItem(BaseModel):
    item: str
    expected_impact: ImpactLevel
    reasoning: str


class ActionPlanItem(BaseModel):
    action: str
    expected_impact: ImpactLevel
    ties_to: Optional[str] = Field(default=None, description="e.g. a specific Portfolio Recommendation or Learning & Certification Agent item, if applicable")


class CareerStrategyOutput(BaseModel):
    role_fit_assessment: FitLevel
    role_fit_reasoning: str

    market_salary_estimate: SalaryEstimate

    seniority_evaluation: str
    seniority_evidence: str

    promotion_readiness_summary: str
    promotion_blockers: List[str] = Field(default_factory=list)
    promotion_accelerants: List[str] = Field(default_factory=list)

    career_risks: List[RankedItem] = Field(default_factory=list, description="Ranked by expected career impact")
    career_opportunities: List[RankedItem] = Field(default_factory=list, description="Ranked by expected career impact")

    thirty_day_plan: List[ActionPlanItem] = Field(default_factory=list)
    ninety_day_plan: List[ActionPlanItem] = Field(default_factory=list)
    one_year_roadmap: List[ActionPlanItem] = Field(default_factory=list)

    sources: List[SourceRef] = Field(default_factory=list, description="Sources the research phase actually cited, e.g. for salary data")
    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    strategy_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

RESEARCH_SYSTEM_PROMPT = """\
You are a compensation researcher inside the AI Career Copilot, a \
multi-agent system. Your job in this phase is ONLY to research current \
market salary data — not to assess fit, seniority, or write career advice.

Use the web_search tool to find current compensation data for the target \
role, company (if given), and location. Prefer company-specific data \
(e.g. Levels.fyi, Glassdoor company pages) over generic market-wide \
figures when a company is named, since it's more relevant — but also \
gather broader market context so the final estimate isn't over-anchored \
on a single noisy source.

Rules:
1. Cite what you find — name the source and figures — inline as you go.
2. If sources disagree significantly (which is common for compensation \
data), say so explicitly rather than picking one number and presenting it \
as settled.
3. Never state a specific salary figure you didn't actually find in a \
search result.
4. Write a concise research brief covering: company-specific data (if \
available), broader role/location market data, and any notable spread or \
disagreement across sources.\
"""

STRUCTURING_SYSTEM_PROMPT = """\
You are the structuring half of the Career Strategy Agent inside the AI \
Career Copilot. You are given a compensation research brief plus the \
candidate's resume and condensed findings from upstream agents (Gap \
Analysis, Skill Evidence, Recruiter Simulation, Portfolio Recommendation, \
Learning & Certification). Convert all of this into the full career \
strategy schema.

Non-negotiable rules:
1. `market_salary_estimate` must be built ONLY from the research brief — \
never invent or adjust a figure the brief didn't support. If the brief \
notes disagreement across sources, reflect that honestly in `reasoning` \
rather than presenting false precision.
2. `role_fit_assessment`, `seniority_evaluation`, and \
`promotion_readiness_summary` must be grounded in the resume and the \
condensed upstream findings you were given — do not re-invent a fit \
judgment that contradicts what Gap Analysis / Skill Evidence / Recruiter \
Simulation already established; synthesize it, don't contradict it.
3. `career_risks` and `career_opportunities` must each be ranked by \
REALISTIC expected career impact (`expected_impact`), not listed in \
arbitrary order, and each needs concrete `reasoning`, not a generic \
statement.
4. Action plan items (`thirty_day_plan`, `ninety_day_plan`, \
`one_year_roadmap`) should reference concrete items from the Portfolio \
Recommendation / Learning & Certification summary via `ties_to` where \
applicable, rather than inventing disconnected generic advice.
5. `promotion_blockers` must be genuine, resume-grounded gaps (e.g. an \
identified critical gap), not vague statements.
6. Set `strategy_confidence` based on how much real resume/market material \
you had to synthesize, not on how promising the candidate's prospects are.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class CareerStrategyAgent(BaseAgent[CareerStrategyInput, CareerStrategyOutput]):
    name = "Career Strategy Agent"
    system_prompt = STRUCTURING_SYSTEM_PROMPT
    input_model = CareerStrategyInput
    output_model = CareerStrategyOutput

    def __init__(self, client: Optional[LLMClient] = None):
        super().__init__(client or LLMClient(max_tokens=16384))

    def build_research_prompt(self, data: CareerStrategyInput) -> str:
        location_hint = f" in {data.location}" if data.location else ""
        company_hint = f" at {data.company_name}" if data.company_name else ""
        return f"Research current market compensation for a '{data.target_role}' role{company_hint}{location_hint}."

    def build_user_prompt(self, data: CareerStrategyInput) -> str:
        raise NotImplementedError("CareerStrategyAgent.run() builds the phase-2 prompt itself; see build_structuring_prompt().")

    def build_structuring_prompt(self, data: CareerStrategyInput, research_brief: str) -> str:
        findings_block = f"\n--- UPSTREAM FINDINGS SUMMARY START ---\n{data.key_findings_summary}\n--- UPSTREAM FINDINGS SUMMARY END ---\n" if data.key_findings_summary else "\n(No upstream findings summary provided — reason from the resume alone for fit/seniority/promotion assessments.)\n"
        plan_block = f"\n--- PORTFOLIO/LEARNING PLAN SUMMARY START ---\n{data.portfolio_and_learning_plan_summary}\n--- PORTFOLIO/LEARNING PLAN SUMMARY END ---\n" if data.portfolio_and_learning_plan_summary else "\n(No portfolio/learning plan summary provided — action plans should stand on their own reasoning.)\n"
        return (
            f"Target role: {data.target_role}"
            + (f"\nTarget company: {data.company_name}" if data.company_name else "")
            + (f"\nLocation: {data.location}" if data.location else "")
            + f"{findings_block}{plan_block}\n"
            "--- COMPENSATION RESEARCH BRIEF START ---\n"
            f"{research_brief}\n"
            "--- COMPENSATION RESEARCH BRIEF END ---\n\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---\n\n"
            "Convert all of this into the structured career strategy schema per your instructions."
        )

    def run(self, data: CareerStrategyInput) -> CareerStrategyOutput:
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
