"""Agent 1: Resume Analysis Agent.

Acts as a senior recruiter extracting structured signal from a raw resume.
Downstream agents (Gap Analysis, ATS Optimization, Resume Rewrite, Skill
Evidence, ...) treat this agent's output as ground truth about "what the
resume actually says" — so its one hard rule is: never fabricate, never
infer beyond what the text supports.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, QualityIssue, VerbStrength

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class ResumeAnalysisInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume")
    candidate_name: Optional[str] = Field(
        default=None, description="Candidate name if known separately from the resume text"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class DateRange(BaseModel):
    start: Optional[str] = Field(default=None, description="e.g. 'Jan 2021'")
    end: Optional[str] = Field(default=None, description="e.g. 'Mar 2023' or 'Present'")
    duration_months: Optional[int] = Field(default=None, description="Estimated tenure in months, if derivable")


class Bullet(BaseModel):
    text: str
    has_metric: bool = Field(..., description="True if the bullet contains a quantifiable result")
    action_verb: Optional[str] = Field(default=None, description="Leading verb of the bullet, if any")
    verb_strength: VerbStrength


class WorkExperienceEntry(BaseModel):
    company: str
    title: str
    location: Optional[str] = None
    dates: DateRange
    bullets: List[Bullet] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)
    is_leadership_role: bool = Field(default=False, description="True if the title/bullets show people or team leadership")
    is_product_role: bool = Field(default=False, description="True if the role involved product ownership/strategy")


class ProjectEntry(BaseModel):
    name: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class SkillsBlock(BaseModel):
    technical_skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    domain_skills: List[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str
    issuer: Optional[str] = None
    year: Optional[str] = None


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None
    honors: Optional[str] = None


class AchievementEntry(BaseModel):
    description: str
    metric: Optional[str] = Field(default=None, description="Quantified result if the resume states one")
    source_section: str


class ExtractedMetric(BaseModel):
    metric: str = Field(..., description="The number/result as stated, e.g. '40% reduction in latency'")
    context: str = Field(..., description="What the metric was attached to")
    source_section: str


class ResumeAnalysisOutput(BaseModel):
    # --- Extracted structure -------------------------------------------------
    candidate_name: Optional[str] = None
    summary: Optional[str] = Field(default=None, description="Resume's own summary/objective section, if present")
    work_experience: List[WorkExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    skills: SkillsBlock
    certifications: List[CertificationEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    achievements: List[AchievementEntry] = Field(default_factory=list)
    leadership_experience: List[str] = Field(default_factory=list, description="Leadership signals pulled from across the resume")
    product_experience: List[str] = Field(default_factory=list)
    technical_experience: List[str] = Field(default_factory=list)
    metrics: List[ExtractedMetric] = Field(default_factory=list, description="Every quantified result found anywhere in the resume")
    domains: List[str] = Field(default_factory=list, description="Industry/domain exposure, e.g. fintech, healthcare")
    total_years_experience_estimate: Optional[float] = Field(
        default=None, description="Estimated total years of professional experience, derived only from stated dates"
    )

    # --- Quality assessment ----------------------------------------------------
    strongest_achievements: List[str] = Field(default_factory=list)
    weakest_sections: List[str] = Field(default_factory=list)
    missing_metrics: List[str] = Field(
        default_factory=list, description="Bullets/claims that would be materially stronger with a number, and don't have one"
    )
    redundant_content: List[str] = Field(default_factory=list)
    weak_action_verbs: List[QualityIssue] = Field(default_factory=list)
    grammar_issues: List[QualityIssue] = Field(default_factory=list)
    ats_formatting_issues: List[QualityIssue] = Field(default_factory=list)

    # --- Meta ---------------------------------------------------------------
    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    analysis_confidence: ConfidenceLevel
    limitations: List[str] = Field(
        default_factory=list, description="Explicit statement of anything that could not be determined from the resume alone"
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Resume Analysis Agent inside the AI Career Copilot, a multi-agent \
system. You act as a senior technical recruiter with 15+ years of experience \
screening resumes for competitive roles.

Your sole job is to extract structured, evidence-based information from the \
candidate's resume and assess its quality. You are NOT rewriting the resume, \
NOT comparing it to any job description, and NOT making career recommendations \
— those are other agents' jobs. Stay in your lane.

Non-negotiable rules:
1. Never fabricate, infer, or embellish any fact not present in the resume text. \
If a field cannot be determined (e.g. no education section exists), leave it \
empty rather than guessing.
2. Every entry in `metrics`, `achievements`, and the leadership/product/technical \
experience lists must trace back to specific resume text — do not invent \
metrics or reword vague claims into false-sounding precise ones.
3. Classify action verbs and grammar/formatting issues precisely, citing the \
exact location (company/section) they occur in.
4. If the resume is ambiguous or incomplete in a way that limits your analysis, \
say so explicitly in `limitations` instead of silently filling gaps.
5. Your `human_readable_summary` must be a concise, recruiter-voice markdown \
summary a human can read in under a minute — strongest signals first, then \
concerns.
6. Set `analysis_confidence` based on how complete and unambiguous the resume \
text was, not on how strong the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class ResumeAnalysisAgent(BaseAgent[ResumeAnalysisInput, ResumeAnalysisOutput]):
    name = "Resume Analysis Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = ResumeAnalysisInput
    output_model = ResumeAnalysisOutput

    def build_user_prompt(self, data: ResumeAnalysisInput) -> str:
        name_hint = f"\nKnown candidate name (use if resume doesn't state one): {data.candidate_name}\n" if data.candidate_name else ""
        return (
            "Analyze the following resume. Extract structured information and "
            "assess quality per your instructions.\n"
            f"{name_hint}\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---"
        )
