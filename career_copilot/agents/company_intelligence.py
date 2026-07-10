"""Agent 3: Company Intelligence Agent.

Acts as a company research specialist. Unlike Resume/JD Intelligence, this
agent's subject (a real company) isn't handed to it as text — it has to go
find current, verifiable information. That makes fabrication risk much
higher than the first two agents, so this agent runs in two phases instead
of one:

  1. Research: the model uses Anthropic's server-side web_search tool to
     gather current information, in prose, citing what it finds.
  2. Structure: a second, non-searching call shapes that research brief into
     the schema, and is instructed to leave fields empty rather than invent
     anything the brief didn't actually support.

Downstream agents (Career Strategy, Interview Coach, Application Assets)
treat `application_implications` / `interview_prep_implications` as the
bridge between "what's true about this company" and "what the candidate
should do about it."
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class CompanyIntelligenceInput(BaseModel):
    company_name: str = Field(..., description="Name of the company to research")
    target_role: Optional[str] = Field(
        default=None, description="Role the candidate is applying for, used to focus application/interview implications"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ProductLine(BaseModel):
    name: str
    description: str


class NewsItem(BaseModel):
    headline: str
    date: Optional[str] = Field(default=None, description="As precise as the source allows, e.g. 'June 2026'")
    summary: str
    source: Optional[str] = None


class SourceRef(BaseModel):
    title: str
    publisher: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None


class CompanyIntelligenceOutput(BaseModel):
    company_name: str
    industry: str
    products: List[ProductLine] = Field(default_factory=list)
    customers: List[str] = Field(default_factory=list, description="Customer segments and/or notable named customers")
    competitors: List[str] = Field(default_factory=list)
    revenue_model: str
    ai_initiatives: List[str] = Field(default_factory=list)
    product_strategy: str
    engineering_culture: str
    product_culture: str
    leadership_principles: List[str] = Field(default_factory=list)
    hiring_philosophy: str
    tech_stack: List[str] = Field(default_factory=list, description="Only technologies with a source; empty if none found")
    recent_news: List[NewsItem] = Field(default_factory=list)
    funding_stage: Optional[str] = None
    future_direction: str

    # --- Bridge to the candidate's application ---------------------------------
    application_implications: List[str] = Field(
        default_factory=list, description="How these findings should shape the resume/application materials"
    )
    interview_prep_implications: List[str] = Field(
        default_factory=list, description="How these findings should shape interview preparation"
    )

    # --- Meta ---------------------------------------------------------------
    sources: List[SourceRef] = Field(default_factory=list, description="Sources the research brief actually cited")
    unverified_or_assumed: List[str] = Field(
        default_factory=list,
        description="Claims elsewhere in this output that are inferred, anecdotal (e.g. forum/review-site sourced), or hedged in the research brief rather than confirmed by a primary source — stated explicitly rather than silently blended in",
    )
    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    research_confidence: ConfidenceLevel
    limitations: List[str] = Field(
        default_factory=list, description="Explicit statement of anything that could not be determined via research"
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

RESEARCH_SYSTEM_PROMPT = """\
You are a company research specialist inside the AI Career Copilot, a \
multi-agent system helping a candidate prepare a job application. Your job \
in this phase is ONLY to research — not to format or advise.

Use the web_search tool to gather current, verifiable information about the \
target company across: industry, products, customers, competitors, revenue \
model, AI initiatives, product strategy, engineering culture, product \
culture, leadership principles, hiring philosophy, tech stack, recent news, \
funding stage, and future direction.

Rules:
1. Prefer primary/official sources (company blog, careers page, official \
press releases, regulatory filings) over forums or aggregators; when you \
use a secondary or anecdotal source (e.g. Glassdoor, Blind, a listicle), say \
so explicitly in your prose.
2. Cite what you find — name the source and, where available, its date — \
inline as you go, so a later step can extract them.
3. Never state something as fact if your search didn't actually support it. \
If you can't find reliable information on one of the topics above, say so \
plainly instead of guessing or relying on general knowledge you're not \
confident is current.
4. Write a thorough, organized prose research brief covering each topic \
above as a labeled section. This brief will be converted into structured \
data by a separate step, so completeness and source attribution matter more \
than polish.\
"""

STRUCTURING_SYSTEM_PROMPT = """\
You are the structuring half of the Company Intelligence Agent inside the \
AI Career Copilot. You are given a research brief about a company, produced \
by a prior step that used live web search, plus the candidate's target role. \
Your job is to convert that brief into the structured schema — you do not \
have search access and must not add any fact the brief doesn't contain.

Non-negotiable rules:
1. Every field must trace back to something stated in the research brief. If \
the brief doesn't cover a topic (e.g. tech stack), leave that field empty \
and add a note to `limitations` — do not fill it from general knowledge.
2. Populate `sources` from whatever citations/attributions appear in the \
brief (source name, publisher, date, URL if given).
3. Populate `unverified_or_assumed` with any claim used elsewhere in your \
output that the brief itself flagged as anecdotal, secondary-sourced, \
hedged, or inferred (e.g. sourced from Glassdoor/Blind rather than an \
official source) — do not silently blend uncertain claims in as if verified.
4. `application_implications` and `interview_prep_implications` must be \
specific to the candidate's target role, not generic advice — ground each \
one in a specific finding above it.
5. Set `research_confidence` based on how much of the brief was grounded in \
primary sources versus thin or anecdotal, not on how impressive the company is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class CompanyIntelligenceAgent(BaseAgent[CompanyIntelligenceInput, CompanyIntelligenceOutput]):
    name = "Company Intelligence Agent"
    system_prompt = STRUCTURING_SYSTEM_PROMPT
    input_model = CompanyIntelligenceInput
    output_model = CompanyIntelligenceOutput

    def build_research_prompt(self, data: CompanyIntelligenceInput) -> str:
        role_hint = f" for a candidate targeting the '{data.target_role}' role" if data.target_role else ""
        return f"Research the company '{data.company_name}'{role_hint}. Cover every topic listed in your instructions."

    def build_user_prompt(self, data: CompanyIntelligenceInput) -> str:
        # Not used directly by run() below (which needs the research brief interleaved),
        # but kept so this agent's phase-2 prompt shape is documented and testable in isolation.
        raise NotImplementedError("CompanyIntelligenceAgent.run() builds the phase-2 prompt itself; see build_structuring_prompt().")

    def build_structuring_prompt(self, data: CompanyIntelligenceInput, research_brief: str) -> str:
        role_hint = f"\nCandidate's target role: {data.target_role}\n" if data.target_role else ""
        return (
            f"Company: {data.company_name}{role_hint}\n"
            "--- RESEARCH BRIEF START ---\n"
            f"{research_brief}\n"
            "--- RESEARCH BRIEF END ---\n\n"
            "Convert this research brief into the structured schema per your instructions."
        )

    def run(self, data: CompanyIntelligenceInput) -> CompanyIntelligenceOutput:
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
