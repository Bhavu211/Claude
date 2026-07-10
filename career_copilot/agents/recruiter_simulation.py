"""Agent 10: Recruiter Simulation Agent.

Simulates a recruiter's realistic first-pass resume screen: the blunt,
time-pressured 30-second reaction, not a careful multi-page analysis. This
agent is deliberately more subjective in voice than the analytical agents
(Gap Analysis, Skill Evidence, ...) — real recruiters form snap judgments
and make reasonable inferences from incomplete information, and sanitizing
that away would defeat the point of a "what would actually happen" gut
check.

The line this agent must not cross: impressions, inferences, and reactions
can be blunt and subjective (that's the value), but every strength,
concern, missing-information item, and reject/shortlist reason must trace
to something actually present (or actually absent) in the resume or JD —
never an invented specific about the candidate.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class RecruiterSimulationInput(BaseModel):
    resume_text: str = Field(..., description="Full plain-text content of the candidate's resume")
    jd_text: str = Field(..., description="Full plain-text content of the target job description")
    company_name: Optional[str] = Field(default=None, description="Target company, if not already clear from the JD")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class ScreeningDecision(str, Enum):
    STRONG_SHORTLIST = "strong_shortlist"
    SHORTLIST = "shortlist"
    SHORTLIST_WITH_RESERVATIONS = "shortlist_with_reservations"
    REJECT = "reject"


class RecruiterSimulationOutput(BaseModel):
    first_impression: str = Field(..., description="The gut reaction from the first few seconds of scanning — what catches the eye first, in what order")
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list, description="What a recruiter would want to see but doesn't find on the page")
    likely_interview_questions: List[str] = Field(
        default_factory=list, description="Screening-call-level questions a recruiter would actually ask, not deep technical ones"
    )
    reasons_to_shortlist: List[str] = Field(default_factory=list, description="Must exist even if the overall lean is toward rejection")
    reasons_to_reject: List[str] = Field(default_factory=list, description="Must exist even if the overall lean is toward shortlisting — real screens weigh both sides")

    hiring_recommendation: ScreeningDecision
    recommendation_reasoning: str = Field(..., description="Must weigh the shortlist and reject reasons against each other, not just restate the decision")

    human_readable_summary: str = Field(..., description="Markdown summary of this analysis for a human reader")
    simulation_confidence: ConfidenceLevel = Field(..., description="Confidence in how representative this simulation is, not confidence in the candidate")
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Recruiter Simulation Agent inside the AI Career Copilot, a \
multi-agent system. You act as a busy in-house recruiter doing a first-pass \
screen — you have roughly 30 seconds of real attention for this resume \
before deciding whether it's worth a closer look, and you are being asked \
to render that reaction honestly, not diplomatically.

Your sole job is this simulated screen. You are NOT doing a deep skills \
audit or gap analysis — those are other agents' jobs, and this agent's \
value is precisely that it's faster and blunter than they are. Stay in \
your lane.

Non-negotiable rules:
1. Your impressions and inferences may be genuinely subjective and blunt — \
that's the point of this agent. A real recruiter forms snap judgments from \
incomplete information, and you should too.
2. However, every `strength`, `concern`, `missing_information` item, and \
shortlist/reject reason MUST trace to something actually present (or \
actually absent) in the resume or JD text you were given — never invent a \
specific fact about the candidate (an employer, a number, a credential) \
that isn't there, even in service of a more dramatic reaction.
3. `first_impression` should read like a real, fast top-to-bottom scan — \
what catches the eye first, in what order — not a summary written after \
careful analysis.
4. Populate BOTH `reasons_to_shortlist` and `reasons_to_reject` regardless \
of which way your final recommendation leans — a real screen weighs both \
sides before deciding, and a one-sided list undermines the recommendation's \
credibility.
5. `likely_interview_questions` should be screening-call-level (motivation, \
logistics, one or two questions probing the resume's thin spots) — not deep \
technical/case questions; that's Interview Coach Agent's job.
6. `recommendation_reasoning` must explicitly weigh the shortlist reasons \
against the reject reasons, not just restate the decision.
7. Set `simulation_confidence` based on how much the resume and JD gave you \
to react to, not on how strong the candidate is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class RecruiterSimulationAgent(BaseAgent[RecruiterSimulationInput, RecruiterSimulationOutput]):
    name = "Recruiter Simulation Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = RecruiterSimulationInput
    output_model = RecruiterSimulationOutput

    def build_user_prompt(self, data: RecruiterSimulationInput) -> str:
        company_hint = f"\nTarget company: {data.company_name}\n" if data.company_name else ""
        return (
            "Simulate a recruiter's first-pass 30-second screen of the following resume against the "
            "job description, per your instructions.\n"
            f"{company_hint}\n"
            "--- JOB DESCRIPTION TEXT START ---\n"
            f"{data.jd_text}\n"
            "--- JOB DESCRIPTION TEXT END ---\n\n"
            "--- RESUME TEXT START ---\n"
            f"{data.resume_text}\n"
            "--- RESUME TEXT END ---"
        )
