"""LLM-as-judge scoring for the eval harness.

This is deliberately separate from Critic Agent (career_copilot/agents/critic.py).
Critic Agent is a *production* component: it reviews a real session's actual
15 agent outputs together, cross-checking them against each other and against
resume/JD ground truth. This judge is a *development-time* tool: it scores one
agent's output on one test case in isolation, run across the 10-20 varied
inputs (easy/normal/edge/bad-input/missing-info) a developer uses to validate
an agent before shipping a prompt change — the workflow Phase 1 of the
project's evaluation plan calls for.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class JudgeInput(BaseModel):
    agent_name: str
    agent_purpose: str = Field(..., description="What this agent is supposed to do, for the judge's context")
    case_category: str = Field(..., description="e.g. 'easy', 'normal', 'edge', 'bad_input', 'missing_information'")
    case_description: str = Field(..., description="What this specific test case is checking for")
    input_summary: str = Field(..., description="The input actually given to the agent, as text")
    output_json: str = Field(..., description="The agent's actual output, serialized as JSON")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class JudgeVerdict(BaseModel):
    accuracy: int = Field(..., ge=0, le=100, description="Does the output correctly reflect the input?")
    completeness: int = Field(..., ge=0, le=100, description="Does it cover what the input actually contains/asks?")
    consistency: int = Field(..., ge=0, le=100, description="Internal consistency — no self-contradiction, no arithmetic mismatch")
    hallucination_detected: bool = Field(..., description="True if the output states anything not traceable to the input")
    hallucination_notes: Optional[str] = Field(default=None, description="Specifics if hallucination_detected is true; null otherwise")
    handles_edge_case_well: Optional[bool] = Field(
        default=None,
        description="For edge/bad_input/missing_information cases: did the agent respond appropriately "
        "(e.g. null/insufficient-evidence rather than a fabricated answer)? Null for easy/normal cases.",
    )
    overall_score: int = Field(..., ge=0, le=100)
    reasoning: str = Field(..., description="Specific, evidence-based — cite what in the output supports the scores")
    judge_confidence: ConfidenceLevel


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an evaluation judge for the AI Career Copilot system. You score a \
single agent's output against a single test case, as part of a development-\
time validation suite — not a production review.

Non-negotiable rules:
1. Score `accuracy` and `completeness` against the ACTUAL input given, not \
against what a generic version of this agent might ideally produce.
2. `hallucination_detected` must be true if ANY claim in the output isn't \
traceable to the input — a name, a metric, a source, a fact. This is the \
single most important field; false negatives here are the worst failure \
mode of this judge.
3. For `case_category` values of 'edge', 'bad_input', or 'missing_information': \
set `handles_edge_case_well` based on whether the agent responded honestly \
(null fields, an explicit limitation, a request for missing info) rather than \
inventing a plausible-looking answer to paper over the gap. For 'easy' or \
'normal' cases, leave `handles_edge_case_well` null — it doesn't apply.
4. `overall_score` should weight hallucination and edge-case handling most \
heavily — a fluent, well-structured output that hallucinates is a worse \
failure than a rough one that's honest.
5. `reasoning` must cite specifics from the output, not restate the scores \
in prose.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class JudgeAgent(BaseAgent[JudgeInput, JudgeVerdict]):
    name = "Eval Judge"
    system_prompt = SYSTEM_PROMPT
    input_model = JudgeInput
    output_model = JudgeVerdict

    def build_user_prompt(self, data: JudgeInput) -> str:
        return (
            f"Agent under test: {data.agent_name}\n"
            f"Agent's purpose: {data.agent_purpose}\n"
            f"Test case category: {data.case_category}\n"
            f"Test case description: {data.case_description}\n\n"
            f"--- INPUT GIVEN TO THE AGENT ---\n{data.input_summary}\n\n"
            f"--- AGENT'S ACTUAL OUTPUT ---\n{data.output_json}\n\n"
            "Score this output per your instructions."
        )
