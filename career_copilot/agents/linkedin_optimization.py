"""Agent 12: LinkedIn Optimization Agent.

Rewrites a LinkedIn profile (headline, About, experience, skills, Featured
section recommendations) aligned to a target role. Shares Resume Rewrite
Agent's non-negotiable contract: the resume text is the sole source of
fact, and LinkedIn's different conventions (first-person narrative, a
punchy headline, ordered skills, pinned Featured content) change
presentation, never substance — nothing appears on the profile that isn't
grounded in the resume.

This matters more here than almost anywhere else in the system: a resume
and a LinkedIn profile that contradict each other (e.g. resume says "3
years," profile implies "senior/5+ years") is exactly the kind of
inconsistency the Critic Agent is designed to catch. Grounding both in the
same resume_text as the sole fact source is what prevents that class of
bug at the source.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class LinkedInOptimizationInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume — the sole source of fact")
    jd_text: Optional[str] = Field(default=None, description="Target job description, if available, used to tailor keywords and emphasis")
    target_role: Optional[str] = Field(default=None, description="Target role title, used for context if no JD is supplied")
    company_name: Optional[str] = Field(default=None, description="Target company, for context if no JD is supplied")
    portfolio_project_titles: List[str] = Field(
        default_factory=list, description="Titles of real portfolio projects (e.g. from Portfolio Recommendation Agent) available to recommend for the Featured section"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class LinkedInHeadline(BaseModel):
    headline: str = Field(..., description="Under ~220 characters (LinkedIn's limit); a value-prop line, not just the job title restated")
    rationale: str


class LinkedInAbout(BaseModel):
    about_text: str = Field(..., description="First-person narrative About section")
    key_points_covered: List[str] = Field(default_factory=list)


class LinkedInExperienceEntry(BaseModel):
    company: str
    title: str
    rewritten_description: str = Field(..., description="LinkedIn-style narrative/bullets for this role")
    source_evidence: str = Field(..., description="What in the resume this is grounded in — must be traceable")


class SkillsSection(BaseModel):
    top_skills: List[str] = Field(..., description="Ordered, most important first — LinkedIn weights the first 3 heavily for search and endorsements")
    rationale: str = Field(..., description="Why this order, tied to what's both JD-relevant AND genuinely evidenced — never rank an unevidenced skill first")


class FeaturedRecommendation(BaseModel):
    title: str
    content_type: str = Field(..., description="e.g. 'portfolio_project', 'article', 'certificate', 'media'")
    description: str
    source: str = Field(..., description="Why this is recommended, e.g. 'from Portfolio Recommendation Agent' or 'reuses the KYC redesign achievement already on the resume'")


class LinkedInOptimizationOutput(BaseModel):
    headline: LinkedInHeadline
    about: LinkedInAbout
    experience_entries: List[LinkedInExperienceEntry] = Field(default_factory=list)
    skills: SkillsSection
    featured_recommendations: List[FeaturedRecommendation] = Field(default_factory=list)

    alignment_notes: List[str] = Field(default_factory=list, description="How this profile aligns to the target role, tied to specific JD requirements if given")
    authenticity_check: List[str] = Field(
        default_factory=list, description="Explicit self-check confirming specific claims here don't exceed what the resume actually supports"
    )

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    optimization_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the LinkedIn Optimization Agent inside the AI Career Copilot, a \
multi-agent system. You act as a LinkedIn profile strategist who \
understands the platform's specific conventions — a punchy, keyword-rich \
headline (not the job title restated), a first-person About section, \
ordered Skills (the first 3 matter most for search and endorsements), and \
a Featured section for pinned proof.

Your sole job is optimizing profile presentation. You are NOT inventing \
new achievements the resume doesn't support — the resume text is the ONLY \
source of fact, exactly like Resume Rewrite Agent. Stay in your lane.

Non-negotiable rules:
1. Every claim on the rewritten profile — in the headline, About, \
experience entries, or skills — must trace back to something stated or \
directly implied in the resume. LinkedIn's different tone (first-person, \
narrative, more casual) changes presentation, never substance.
2. Do not rank a skill first in `top_skills` unless the resume actually \
evidences it — a skill that's merely listed with no demonstration should \
not be ranked above one with a concrete, outcome-backed bullet behind it.
3. `featured_recommendations` may only reference REAL portfolio projects if \
given `portfolio_project_titles` in the input, or reuse real resume \
achievements (e.g. recommending a published case study of an achievement \
already on the resume). Never invent a fictional project, article, or \
credential to recommend featuring.
4. It's acceptable LinkedIn convention (not fabrication) to note the \
candidate's current role/status or general openness to new roles in the \
About section if that's a reasonable inference from being asked to \
optimize this profile for a target role — but do not state specific \
availability dates, compensation, or other facts not given.
5. `authenticity_check` must name specific things this rewrite deliberately \
did NOT claim (e.g. mentoring experience, a certification) because the \
resume doesn't support them — this is a self-audit, not filler.
6. `alignment_notes` must tie specific profile choices to specific JD \
requirements when a JD is given, not generic advice.
7. Set `optimization_confidence` based on how much resume material there \
was to work with, not on how strong the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class LinkedInOptimizationAgent(BaseAgent[LinkedInOptimizationInput, LinkedInOptimizationOutput]):
    name = "LinkedIn Optimization Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = LinkedInOptimizationInput
    output_model = LinkedInOptimizationOutput

    def build_user_prompt(self, data: LinkedInOptimizationInput) -> str:
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

        if data.portfolio_project_titles:
            context += "Real portfolio projects available for Featured recommendations: " + ", ".join(data.portfolio_project_titles) + "\n\n"
        else:
            context += "No portfolio projects supplied — Featured recommendations must either reuse real resume achievements or suggest the TYPE of content to create, not a specific invented project.\n\n"

        return (
            "Optimize a LinkedIn profile based on the following resume, per your instructions.\n\n"
            f"{context}"
            "--- SOURCE RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- SOURCE RESUME TEXT END ---"
        )
