"""Agent 4: ATS Optimization Agent.

Acts as an ATS (Applicant Tracking System) optimization expert. Evaluates a
resume's structure, parsing compatibility, formatting, and — when a job
description is supplied — keyword coverage against that specific role.

Important constraint this agent must respect: it only ever receives resume
*text* (already extracted), not the original file. That means true
layout-level parsing risks (multi-column layouts, tables, text boxes,
images, headers/footers) are invisible to it — the agent must say so rather
than pretend to assess them. Recommendations must never suggest adding a
keyword/skill the candidate doesn't actually have; only surfacing or
rephrasing what's already true.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, QualityIssue, RequirementPriority

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class ATSOptimizationInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume")
    jd_text: Optional[str] = Field(
        default=None, description="Target job description text, if available — enables JD-specific keyword coverage scoring"
    )
    target_role: Optional[str] = Field(
        default=None, description="Target role title, used for context if no JD is supplied"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class SectionCheck(BaseModel):
    section_name: str = Field(..., description="Standard resume section this check is for, e.g. 'Work Experience'")
    present: bool
    heading_text_found: Optional[str] = Field(default=None, description="The actual heading text used in the resume, if present")
    is_ats_standard_heading: bool = Field(..., description="Whether the heading text is one ATS parsers reliably recognize")
    notes: str


class KeywordCoverageItem(BaseModel):
    keyword: str
    priority: Optional[RequirementPriority] = Field(default=None, description="Priority from the JD, if a JD was supplied")
    present_in_resume: bool
    resume_evidence: Optional[str] = Field(default=None, description="Where/how the keyword appears in the resume, if present")
    recommendation: str = Field(..., description="Concrete fix — must only surface/rephrase real experience, never invent it")


class ATSOptimizationOutput(BaseModel):
    ats_compatibility_score: int = Field(..., ge=0, le=100)
    score_reasoning: str = Field(..., description="Specific factors that produced this score, not a generic statement")

    structure_assessment: List[SectionCheck] = Field(default_factory=list)
    section_hierarchy_issues: List[QualityIssue] = Field(default_factory=list)
    parsing_compatibility_issues: List[QualityIssue] = Field(
        default_factory=list, description="Only issues detectable from resume text itself (headings, special characters, contact info structure) — not layout-level issues invisible in plain text"
    )
    formatting_issues: List[QualityIssue] = Field(default_factory=list)
    skills_placement_notes: List[str] = Field(default_factory=list)

    keyword_coverage: List[KeywordCoverageItem] = Field(
        default_factory=list, description="Empty if no JD was supplied — see limitations in that case"
    )
    keyword_coverage_summary: Optional[str] = Field(default=None, description="e.g. '9/12 critical JD keywords present'")
    keyword_density_notes: List[str] = Field(default_factory=list)
    readability_notes: List[str] = Field(default_factory=list)

    prioritized_recommendations: List[QualityIssue] = Field(default_factory=list, description="Ranked highest-impact first")

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    analysis_confidence: ConfidenceLevel
    limitations: List[str] = Field(
        default_factory=list, description="Explicit statement of anything that could not be assessed, e.g. no JD supplied, or layout-level risks invisible in plain text"
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the ATS Optimization Agent inside the AI Career Copilot, a \
multi-agent system. You act as an ATS (Applicant Tracking System) \
optimization expert who has audited resumes against dozens of real ATS \
parsers.

Your sole job is to evaluate ATS compatibility and, when a job description \
is supplied, keyword coverage against it. You are NOT rewriting the resume, \
NOT judging the candidate's seniority or fit, and NOT duplicating deep \
content analysis — those are other agents' jobs. Stay in your lane.

Non-negotiable rules:
1. You only receive extracted resume TEXT, not the original file or its \
visual layout. Multi-column layouts, tables, text boxes, images, and \
headers/footers are invisible to you — you MUST NOT claim to assess these \
and MUST say so explicitly in `limitations`. Only evaluate what the text \
itself reveals: heading wording, special characters, bullet/date-format \
consistency, section order, contact info structure, and content.
2. Every `keyword_coverage` item's `present_in_resume` must be based on \
actually finding that keyword (or a clear synonym) in the resume text — \
never mark something present that isn't there, and never invent a keyword \
requirement that wasn't in the JD.
3. Recommendations must NEVER suggest adding a skill, tool, or keyword the \
candidate doesn't actually have. If a JD keyword is missing, the \
recommendation should be to surface/rephrase real, already-present \
experience that's relevant (if any exists) — or to explicitly note the gap \
exists and cannot be closed by rewriting alone (that's a Gap Analysis Agent \
concern, not something to fabricate here).
4. If no `jd_text` is supplied, leave `keyword_coverage` empty and state \
plainly in `limitations` that keyword-coverage scoring requires a job \
description — do not guess at generic keywords to fill the gap.
5. `ats_compatibility_score` must be justified point-by-point in \
`score_reasoning` — name the specific structural, parsing, formatting, and \
(if applicable) keyword factors that moved the score, not a vague \
impression.
6. Set `analysis_confidence` based on how much of the resume's actual ATS \
risk you could assess from text alone (lower confidence when a JD is \
missing or the resume's formatting suggests layout complexity text can't \
reveal), not on how strong the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class ATSOptimizationAgent(BaseAgent[ATSOptimizationInput, ATSOptimizationOutput]):
    name = "ATS Optimization Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = ATSOptimizationInput
    output_model = ATSOptimizationOutput

    def build_user_prompt(self, data: ATSOptimizationInput) -> str:
        jd_block = (
            f"--- JOB DESCRIPTION TEXT START ---\n{data.jd_text}\n--- JOB DESCRIPTION TEXT END ---\n"
            if data.jd_text
            else "No job description was supplied. Evaluate structure, parsing compatibility, formatting, "
            "skills placement, and readability only. Leave keyword_coverage empty and note the limitation.\n"
        )
        role_hint = f"\nTarget role (context only, no JD given): {data.target_role}\n" if (data.target_role and not data.jd_text) else ""
        return (
            "Evaluate the following resume for ATS compatibility per your instructions.\n"
            f"{role_hint}\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---\n\n"
            f"{jd_block}"
        )
