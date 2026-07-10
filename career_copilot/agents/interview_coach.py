"""Agent 11: Interview Coach Agent.

Generates interview preparation across five categories (HR, behavioral,
technical, product, company-specific) tailored to the resume, JD, and
(optionally) company context.

The hard rule this agent must never break: STAR-format answers for
behavioral questions must be built ONLY from verified resume information.
When a behavioral question probes a gap the resume has no evidence for
(this system's fixtures always surface at least one — e.g. PM mentoring),
this agent must leave `star_answer` empty and say so in `prep_notes`
instead of inventing a plausible-sounding story. An interview coach that
fabricates the candidate's own history is worse than useless.

`company_context` is optional, pre-researched input (typically Company
Intelligence Agent's findings) — this agent does not do its own web
research. Without it, company-specific questions fall back to JD-text-only
grounding and say so in limitations.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel
from career_copilot.core.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class InterviewCoachInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume")
    jd_text: str = Field(..., description="Full plain-text content of the target job description")
    company_name: Optional[str] = Field(default=None, description="Target company name")
    company_context: Optional[str] = Field(
        default=None,
        description="Pre-researched company facts (e.g. from Company Intelligence Agent) to ground company-specific questions; if omitted, those questions stay grounded in the JD text alone",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class STARAnswer(BaseModel):
    situation: str
    task: str
    action: str
    result: str
    source_evidence: str = Field(..., description="The specific resume text this STAR answer is built from — must be traceable, never invented")


class InterviewQuestion(BaseModel):
    question: str
    why_asked: str = Field(..., description="What the interviewer is actually probing for")
    prep_notes: Optional[str] = Field(
        default=None, description="Talking points or how to approach the answer; used for HR/technical/product/company-specific questions, and for behavioral questions with no resume-backed example"
    )
    star_answer: Optional[STARAnswer] = Field(
        default=None, description="Only for behavioral questions with real resume evidence — must be left null rather than fabricated when no evidence exists"
    )


class InterviewCoachOutput(BaseModel):
    hr_questions: List[InterviewQuestion] = Field(default_factory=list)
    behavioral_questions: List[InterviewQuestion] = Field(default_factory=list)
    technical_questions: List[InterviewQuestion] = Field(default_factory=list)
    product_questions: List[InterviewQuestion] = Field(default_factory=list)
    company_specific_questions: List[InterviewQuestion] = Field(default_factory=list)

    preparation_priorities: List[str] = Field(default_factory=list, description="Ranked, highest-risk-first prep items given the resume's actual gaps")

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    prep_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Interview Coach Agent inside the AI Career Copilot, a \
multi-agent system. You act as an interview coach preparing a candidate \
across five interview types: HR/recruiter, behavioral, technical, product, \
and company-specific.

Your sole job is interview preparation. You are NOT re-analyzing gaps or \
scoring ATS compatibility — those are other agents' jobs. Stay in your lane.

Non-negotiable rules:
1. Behavioral questions must be genuinely likely given the JD, and each \
one's `star_answer` must be built ONLY from what the resume actually \
states — Situation, Task, Action, and Result all need to trace to real \
resume content, cited in `source_evidence`. If a behavioral question \
probes something the resume has NO evidence for (this happens — e.g. a \
mentoring/leadership question when the resume shows no mentoring), leave \
`star_answer` null and use `prep_notes` to say so plainly and suggest how \
to handle it honestly in the room — do not invent a plausible-sounding \
story to fill the gap.
2. Technical and product questions must fit the actual role (e.g. for a PM \
role, "technical" means PM-level technical fluency — SQL, working with \
data/ML teams, system understanding — not a software engineering coding \
interview) and the actual domain (use the JD's specific problem space, not \
generic questions).
3. Company-specific questions must be grounded in `company_context` if \
provided; if not provided, ground them in the JD text alone and say so in \
`limitations` rather than inventing company facts you weren't given.
4. `why_asked` must explain the actual interviewer intent, not just \
restate the question.
5. `preparation_priorities` must be ranked by real risk — the resume's \
actual weakest points first, not a generic checklist.
6. Set `prep_confidence` based on how much resume/JD/company material you \
had to ground questions in, not on how ready the candidate seems overall.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class InterviewCoachAgent(BaseAgent[InterviewCoachInput, InterviewCoachOutput]):
    name = "Interview Coach Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = InterviewCoachInput
    output_model = InterviewCoachOutput

    def __init__(self, client: Optional[LLMClient] = None):
        super().__init__(client or LLMClient(max_tokens=16384))

    def build_user_prompt(self, data: InterviewCoachInput) -> str:
        company_block = ""
        if data.company_context:
            company_block = f"--- COMPANY CONTEXT START ---\n{data.company_context}\n--- COMPANY CONTEXT END ---\n\n"
        elif data.company_name:
            company_block = f"Target company: {data.company_name} (no additional research provided — ground company-specific questions in the JD text alone)\n\n"
        else:
            company_block = "No company name or context provided — ground company-specific questions in the JD text alone.\n\n"

        return (
            "Generate interview preparation across all five question categories per your instructions.\n\n"
            f"{company_block}"
            "--- JOB DESCRIPTION TEXT START ---\n"
            f"{data.jd_text}\n"
            "--- JOB DESCRIPTION TEXT END ---\n\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---"
        )
