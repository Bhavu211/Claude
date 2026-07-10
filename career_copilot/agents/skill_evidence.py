"""Agent 7: Skill Evidence Agent.

Verifies every skill-shaped JD requirement (skills, tools, technologies,
domain expertise, leadership, certifications, product experience — not
years-of-experience, which stays Gap Analysis Agent's territory) against
the resume, grading evidence strength rather than just presence.

This deliberately overlaps in subject matter with Gap Analysis Agent but
answers a different question. Gap Analysis asks "does the candidate meet
this requirement, and is any shortfall a resume fix or a real gap." Skill
Evidence asks "how strong is the proof behind this specific skill claim,
and what evidence would make it stronger" — a forensics pass meant to feed
the Interview Coach Agent (which skills need a ready example) and the
Portfolio Recommendation Agent (which skills need a demonstrating project)
downstream, not to re-litigate overall fit.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, RequirementPriority

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class SkillEvidenceInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume")
    jd_text: str = Field(..., description="Full plain-text content of the target job description")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class SkillEvidenceItem(BaseModel):
    skill: str = Field(..., description="The skill, tool, technology, domain, leadership, or certification requirement being verified")
    jd_priority: Optional[RequirementPriority] = Field(default=None, description="Priority this requirement carries in the JD")
    resume_evidence: str = Field(
        ..., description="Verbatim or close paraphrase from the resume; literally 'No evidence available.' if none exists"
    )
    confidence: ConfidenceLevel = Field(..., description="How strongly the evidence supports genuine proficiency, not just a keyword match")
    missing_proof: Optional[str] = Field(
        default=None, description="What specific evidence would raise confidence; null only when confidence is already HIGH"
    )
    recommendation: str = Field(
        ..., description="How to strengthen the evidence — a resume bullet, an interview-ready example, or a portfolio project — not an overall-fit judgment"
    )


class SkillEvidenceOutput(BaseModel):
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    skills: List[SkillEvidenceItem] = Field(default_factory=list)

    well_evidenced_skills: List[str] = Field(default_factory=list, description="Skills with HIGH confidence evidence")
    weakly_evidenced_skills: List[str] = Field(default_factory=list, description="Skills with LOW or NONE confidence evidence")
    overall_evidence_strength: str = Field(..., description="Narrative synthesis of how well-proven this candidate's skill claims are as a whole")

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    analysis_confidence: ConfidenceLevel = Field(..., description="This agent's confidence in its own analysis, not any individual skill's confidence")
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Skill Evidence Agent inside the AI Career Copilot, a \
multi-agent system. You act as a skeptical technical interviewer whose job \
is to grade how well-proven each of a candidate's claimed skills actually \
is, not just whether the words appear somewhere in the resume.

Your sole job is skill-by-skill evidence grading. You are NOT judging \
overall JD fit, NOT scoring ATS compatibility, and NOT rewriting anything — \
those are other agents' jobs (Gap Analysis Agent already covers overall \
requirement-by-requirement fit; do not duplicate its "is this a gap" \
framing — your framing is "how strong is the proof"). Stay in your lane.

Non-negotiable rules:
1. Cover every skill-shaped requirement in the JD: skills, tools, \
technologies, domain expertise, leadership/mentoring, certifications, and \
product experience. Do not include pure years-of-experience requirements — \
those aren't evidenced the same way a skill is.
2. Grade `confidence` on evidence STRENGTH, not mere presence: HIGH means a \
resume bullet demonstrates the skill in action with a concrete outcome; \
MEDIUM means the skill is mentioned in context but without a clear outcome, \
or appears in multiple places; LOW means it's only listed as a bare skill \
with no demonstrating bullet anywhere; NONE means nothing in the resume \
supports it at all.
3. When confidence is NONE, `resume_evidence` MUST be the literal string \
"No evidence available." — do not paraphrase around this or soften it.
4. `missing_proof` must name the SPECIFIC kind of evidence that would raise \
confidence (e.g. "a bullet describing a specific decision informed by SQL \
analysis"), not a generic "add more detail." Leave it null only when \
confidence is already HIGH.
5. `recommendation` must be about strengthening evidence — a resume bullet \
to add, an interview-ready example to prepare, or a portfolio project to \
build — never a verdict on whether the candidate is a good overall fit.
6. Set `analysis_confidence` based on how clearly the JD's skill \
requirements and the resume's content could be matched, not on how strong \
any individual skill's evidence is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class SkillEvidenceAgent(BaseAgent[SkillEvidenceInput, SkillEvidenceOutput]):
    name = "Skill Evidence Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = SkillEvidenceInput
    output_model = SkillEvidenceOutput

    def build_user_prompt(self, data: SkillEvidenceInput) -> str:
        return (
            "Verify every skill-shaped requirement in the following job description against the resume, "
            "per your instructions.\n\n"
            "--- JOB DESCRIPTION TEXT START ---\n"
            f"{data.jd_text}\n"
            "--- JOB DESCRIPTION TEXT END ---\n\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---"
        )
