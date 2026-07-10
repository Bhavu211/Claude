"""Machine-readable catalog of every specialist agent in the system.

The orchestration agents (Planner, Critic, Supervisor) need to reason about
which agents exist, what they need, and how they depend on each other —
without hallucinating an agent that isn't real or inventing a dependency
that doesn't exist. This module is the single source of truth they draw on,
built directly from how each agent is actually implemented (see each
agent's `build_user_prompt` / `run` for what it truly requires).

`depends_on` is a *quality/synthesis* dependency, not always a hard
technical block — e.g. Interview Coach Agent can run without
Company Intelligence Agent's output (it falls back to JD-text-only
grounding), but produces better company-specific questions with it. Where
a dependency is a hard requirement (the agent's input model has no default
for that field), it's noted in `requires`.
"""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class AgentCategory(str, Enum):
    EXTRACTION = "extraction"  # re-derives findings directly from resume/JD text
    RESEARCH = "research"  # two-phase: web search, then structure
    SYNTHESIS = "synthesis"  # takes other agents' structured findings as input
    REPORT = "report"  # consolidates everything


class AgentSpec(BaseModel):
    id: str = Field(..., description="Matches the module name under career_copilot/agents/")
    name: str
    description: str
    category: AgentCategory
    requires: List[str] = Field(..., description="Hard-required inputs — the agent cannot run without these")
    optional_inputs: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list, description="Other agent ids this one's output quality depends on")


AGENT_REGISTRY: List[AgentSpec] = [
    AgentSpec(
        id="resume_analysis",
        name="Resume Analysis Agent",
        description="Extracts structured, evidence-based signal from a resume: experience, skills, metrics, quality issues.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text"],
    ),
    AgentSpec(
        id="jd_intelligence",
        name="JD Intelligence Agent",
        description="Decodes a job description into prioritized requirements, hidden expectations, and recruiter intent.",
        category=AgentCategory.EXTRACTION,
        requires=["jd_text"],
    ),
    AgentSpec(
        id="company_intelligence",
        name="Company Intelligence Agent",
        description="Researches a real company via live web search: products, culture, funding, AI initiatives, recent news.",
        category=AgentCategory.RESEARCH,
        requires=["company_name"],
        optional_inputs=["target_role"],
    ),
    AgentSpec(
        id="ats_optimization",
        name="ATS Optimization Agent",
        description="Scores ATS compatibility and, if a JD is given, keyword coverage against it.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text"],
        optional_inputs=["jd_text", "target_role"],
    ),
    AgentSpec(
        id="resume_rewrite",
        name="Resume Rewrite Agent",
        description="Rewrites the resume into ATS/Recruiter/Startup/Enterprise/Executive versions, facts unchanged.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text"],
        optional_inputs=["jd_text", "target_role", "company_name"],
    ),
    AgentSpec(
        id="gap_analysis",
        name="Gap Analysis Agent",
        description="Compares resume against JD requirement-by-requirement: presence, evidence, severity, recommendation.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text", "jd_text"],
    ),
    AgentSpec(
        id="skill_evidence",
        name="Skill Evidence Agent",
        description="Grades evidence *strength* (not just presence) for every skill-shaped JD requirement.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text", "jd_text"],
    ),
    AgentSpec(
        id="recruiter_simulation",
        name="Recruiter Simulation Agent",
        description="Simulates a recruiter's blunt, time-pressured 30-second first-pass resume screen.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text", "jd_text"],
    ),
    AgentSpec(
        id="portfolio_recommendation",
        name="Portfolio Recommendation Agent",
        description="Designs portfolio projects to close specific, already-identified skill gaps.",
        category=AgentCategory.SYNTHESIS,
        requires=["target_role", "gaps_to_close"],
        optional_inputs=["company_name", "candidate_background"],
        depends_on=["gap_analysis", "skill_evidence"],
    ),
    AgentSpec(
        id="learning_certification",
        name="Learning & Certification Agent",
        description="Builds a sequenced learning roadmap and grades certification ROI, grounded in live web research.",
        category=AgentCategory.RESEARCH,
        requires=["target_role", "missing_competencies"],
        optional_inputs=["company_name", "certifications_under_consideration", "candidate_background"],
        depends_on=["gap_analysis", "skill_evidence"],
    ),
    AgentSpec(
        id="interview_coach",
        name="Interview Coach Agent",
        description="Generates HR/behavioral/technical/product/company-specific interview questions with resume-backed STAR answers.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text", "jd_text"],
        optional_inputs=["company_context"],
        depends_on=["company_intelligence"],
    ),
    AgentSpec(
        id="linkedin_optimization",
        name="LinkedIn Optimization Agent",
        description="Rewrites headline, About, experience, skills, and Featured recommendations for LinkedIn's conventions.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text"],
        optional_inputs=["jd_text", "target_role", "company_name", "portfolio_project_titles"],
        depends_on=["portfolio_recommendation"],
    ),
    AgentSpec(
        id="application_assets",
        name="Application Assets Agent",
        description="Drafts cover letter, outreach, LinkedIn request, referral request, follow-up, and thank-you emails.",
        category=AgentCategory.EXTRACTION,
        requires=["resume_text"],
        optional_inputs=["jd_text", "company_context", "recruiter_or_hiring_manager_name"],
        depends_on=["company_intelligence"],
    ),
    AgentSpec(
        id="career_strategy",
        name="Career Strategy Agent",
        description="Advises on role fit, market salary (live-researched), seniority, promotion readiness, and a 30/90/365-day plan.",
        category=AgentCategory.RESEARCH,
        requires=["resume_text", "target_role"],
        optional_inputs=["company_name", "location", "key_findings_summary", "portfolio_and_learning_plan_summary"],
        depends_on=["gap_analysis", "skill_evidence", "recruiter_simulation", "portfolio_recommendation", "learning_certification"],
    ),
    AgentSpec(
        id="final_report",
        name="Final Report Agent",
        description="Consolidates every upstream agent's summary into one coherent, non-duplicative executive report and readiness dashboard.",
        category=AgentCategory.REPORT,
        requires=["candidate_name", "target_role"],
        optional_inputs=["company_name"] + [f"{a}_summary" for a in [
            "resume_analysis", "jd_intelligence", "company_intelligence", "ats_optimization", "resume_rewrite",
            "gap_analysis", "skill_evidence", "portfolio_recommendation", "learning_certification",
            "recruiter_simulation", "interview_coach", "linkedin_optimization", "application_assets", "career_strategy",
        ]],
        depends_on=[
            "resume_analysis", "jd_intelligence", "company_intelligence", "ats_optimization", "resume_rewrite",
            "gap_analysis", "skill_evidence", "portfolio_recommendation", "learning_certification",
            "recruiter_simulation", "interview_coach", "linkedin_optimization", "application_assets", "career_strategy",
        ],
    ),
]

AGENT_BY_ID = {spec.id: spec for spec in AGENT_REGISTRY}
