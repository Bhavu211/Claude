"""Agent 16: Planner Agent.

Orchestrates the workflow: detects user intent, decides which of the 15
specialist agents to run (and which to skip, and why), sequences them into
parallel groups and dependencies, flags missing inputs, resolves conflicts
between agents' outputs, assigns priorities, and estimates execution cost.

This agent never analyzes a resume, JD, or company itself — it only plans.
Its entire "knowledge" of what agents exist and how they depend on each
other comes from `AGENT_REGISTRY` (core/registry.py), the same registry the
system's agents are actually built from. This is deliberate: a planner that
free-associates about what agents "probably" exist would eventually
hallucinate a dependency or invent an agent — grounding it in the real
registry makes that structurally impossible.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel
from career_copilot.core.registry import AGENT_REGISTRY

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class PlannerInput(BaseModel):
    user_goal: str = Field(..., description="The user's own words describing what they want")
    has_resume: bool = Field(..., description="Whether resume text is available")
    has_jd: bool = Field(default=False, description="Whether a job description is available")
    has_company_name: bool = Field(default=False, description="Whether a target company name is available")
    years_of_experience_provided: bool = Field(default=False, description="Whether YOE was explicitly given (vs. only derivable from the resume)")
    previous_outputs_available: List[str] = Field(
        default_factory=list, description="Agent ids already run in this session, if resuming a partial pipeline"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserIntent(BaseModel):
    primary_intent: str = Field(..., description="e.g. 'complete_application_package', 'ats_improvement', 'interview_preparation'")
    secondary_intents: List[str] = Field(default_factory=list)
    reasoning: str


class AgentExecutionItem(BaseModel):
    agent_id: str = Field(..., description="Must match an id in AGENT_REGISTRY — never invent one")
    action: str = Field(..., description="'run' or 'skip'")
    reason: str
    priority: Priority
    depends_on: List[str] = Field(default_factory=list, description="agent_ids that must complete first, per AGENT_REGISTRY")


class ParallelGroup(BaseModel):
    group_label: str
    agent_ids: List[str]
    reasoning: str = Field(..., description="Why these can run together — no dependency edges between them")


class MissingInput(BaseModel):
    input_name: str
    blocks_agents: List[str]
    request_message: str = Field(..., description="What to actually ask the user for — specific, not vague")


class ConflictResolution(BaseModel):
    conflict: str
    resolution: str
    reasoning: str


class ExecutionCostEstimate(BaseModel):
    complexity: str = Field(..., description="'low', 'medium', or 'high'")
    agent_count: int
    estimated_time_minutes: str = Field(..., description="A range, e.g. '15-25 minutes'")
    confidence: ConfidenceLevel


class PlannerOutput(BaseModel):
    user_intent: UserIntent
    execution_plan: List[AgentExecutionItem] = Field(..., description="One entry per agent in AGENT_REGISTRY — run or skip, always with a reason")
    parallel_groups: List[ParallelGroup] = Field(default_factory=list)
    missing_inputs: List[MissingInput] = Field(default_factory=list)
    conflicts_resolved: List[ConflictResolution] = Field(default_factory=list, description="Empty if none were found — do not invent one to fill this")
    estimated_completion: ExecutionCostEstimate
    risks: List[str] = Field(default_factory=list)
    final_execution_strategy: str = Field(..., description="Narrative tying the plan together")

    human_readable_summary: str = Field(..., description="Markdown summary of this plan for a human reader")
    planning_confidence: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Planner Agent inside the AI Career Copilot, a multi-agent \
system. You orchestrate a roster of 15 specialist agents — you do NOT \
analyze resumes, job descriptions, or companies yourself, and you never \
generate career content. Your only job is producing a correct execution \
plan.

You will be given the full AGENT_REGISTRY: every agent's id, what it \
requires, what it optionally accepts, and which other agents its output \
quality depends on. This registry is ground truth.

Non-negotiable rules:
1. NEVER reference an agent_id that isn't in the registry you were given, \
and never invent a dependency between agents that the registry doesn't \
state. If you're unsure whether something is a hard requirement or a soft \
quality dependency, treat the registry's `requires` as hard-blocking and \
`depends_on` as ordering-for-quality, not a strict block.
2. `execution_plan` must cover every agent in the registry — each with an \
explicit 'run' or 'skip' and a specific reason tied to the user's actual \
intent, not a generic one.
3. `parallel_groups` must only place agents together that have no \
dependency edge between them per the registry (a agent depending on \
another cannot be in the same group as what it depends on).
4. Detect `missing_inputs` by checking each 'run' agent's `requires` \
against what the user actually provided (has_resume, has_jd, \
has_company_name) — flag only genuinely blocking gaps, and write a \
specific, actionable `request_message` for each, not a vague one.
5. `conflicts_resolved` must be empty unless you're given information \
showing upstream agents actually disagreed — never invent a conflict to \
have something to report. If no conflicts exist, say so plainly rather \
than fabricating one.
6. Assign `priority` per task based on the user's actual stated intent — \
not every agent is 'critical' just because it exists.
7. `estimated_completion` should account for real cost drivers: agents \
using live web research (Company Intelligence, Learning & Certification, \
Career Strategy) take meaningfully longer than single-pass agents, and \
agent_count alone doesn't capture that.
8. Set `planning_confidence` based on how clear the user's intent and how \
complete their inputs were, not on how ambitious the resulting plan is.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class PlannerAgent(BaseAgent[PlannerInput, PlannerOutput]):
    name = "Planner Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = PlannerInput
    output_model = PlannerOutput

    def build_user_prompt(self, data: PlannerInput) -> str:
        registry_block = "\n".join(
            f"- id: {spec.id}\n"
            f"  name: {spec.name}\n"
            f"  category: {spec.category.value}\n"
            f"  description: {spec.description}\n"
            f"  requires: {spec.requires}\n"
            f"  optional_inputs: {spec.optional_inputs}\n"
            f"  depends_on: {spec.depends_on}"
            for spec in AGENT_REGISTRY
        )

        inputs_block = (
            f"has_resume: {data.has_resume}\n"
            f"has_jd: {data.has_jd}\n"
            f"has_company_name: {data.has_company_name}\n"
            f"years_of_experience_provided: {data.years_of_experience_provided}\n"
            f"previous_outputs_available: {data.previous_outputs_available or 'none'}"
        )

        return (
            f"User goal (their own words): {data.user_goal}\n\n"
            f"Available inputs:\n{inputs_block}\n\n"
            "--- AGENT_REGISTRY START ---\n"
            f"{registry_block}\n"
            "--- AGENT_REGISTRY END ---\n\n"
            "Produce a full execution plan per your instructions, covering every agent in the registry."
        )
