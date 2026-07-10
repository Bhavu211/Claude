"""Agent 18: Supervisor Agent.

The top-level entry point for the whole system. The Supervisor does not
analyze a resume, a JD, or a company, and it does not write career content
of its own — it coordinates. It cross-checks what the Planner Agent said
should run against what actually ran, cross-checks every issue the Critic
Agent found against what's since been fixed, carries forward every
limitation/insufficient-evidence flag any constituent agent raised, and
renders a single go/no-go verdict on whether the package is ready to hand
to the user.

Like Planner and Critic, it grounds itself in the real `AGENT_REGISTRY` so
its orchestration log can never reference an agent that doesn't exist. It
never marks an issue "resolved" without a stated fix to point to, and it
never reports a quality gate rosier than the actual open-issue count
supports.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.common import ConfidenceLevel, Severity
from career_copilot.core.registry import AGENT_REGISTRY

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class SupervisorInput(BaseModel):
    candidate_name: str
    target_role: str
    company_name: Optional[str] = None
    user_goal: str = Field(..., description="The user's own words describing what they wanted")

    planner_output: str = Field(..., description="Full JSON output of the Planner Agent for this session")
    completed_agent_ids: List[str] = Field(
        default_factory=list, description="agent_ids that actually produced output in this session"
    )
    failed_agent_ids: List[str] = Field(
        default_factory=list, description="agent_ids the plan called for that errored out or never returned"
    )

    critic_output: Optional[str] = Field(
        default=None, description="Full JSON output of the Critic Agent for this session, if a review was run"
    )
    post_critic_fixes_applied: List[str] = Field(
        default_factory=list,
        description="Short descriptions of fixes made to any agent's output after the Critic review, if any",
    )
    final_report_output: Optional[str] = Field(
        default=None, description="Full JSON output of the Final Report Agent, if it has run"
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class AgentRunStatus(str, Enum):
    RAN = "ran"
    SKIPPED_PER_PLAN = "skipped_per_plan"
    PLANNED_BUT_NOT_RUN = "planned_but_not_run"
    RAN_BUT_NOT_PLANNED = "ran_but_not_planned"
    FAILED = "failed"


class OrchestrationRecord(BaseModel):
    agent_id: str = Field(..., description="Must match an id in AGENT_REGISTRY")
    status: AgentRunStatus
    note: str = Field(..., description="What the plan said vs. what actually happened, specifically")


class IssueStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    UNVERIFIABLE = "unverifiable"


class IssueResolution(BaseModel):
    agent_id: str = Field(..., description="Must match an id in AGENT_REGISTRY")
    issue: str
    severity: Severity
    status: IssueStatus
    evidence: str = Field(
        ...,
        description="What specifically confirms resolution (a matching fix description), or why it's still open/unverifiable",
    )


class QualityGateStatus(str, Enum):
    PASSED = "passed"
    PASSED_WITH_NOTES = "passed_with_notes"
    HELD_FOR_REVISION = "held_for_revision"
    BLOCKED = "blocked"


class SessionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class SupervisorOutput(BaseModel):
    session_status: SessionStatus
    orchestration_log: List[OrchestrationRecord] = Field(
        ..., description="One entry per agent in AGENT_REGISTRY, cross-checking planned vs. actual"
    )
    plan_adherence_issues: List[str] = Field(
        default_factory=list, description="Empty only if execution matched the plan exactly"
    )

    quality_gate: QualityGateStatus
    issue_resolutions: List[IssueResolution] = Field(
        default_factory=list, description="Every critical/major issue the Critic found, cross-checked against post_critic_fixes_applied"
    )
    open_blocking_issues: List[str] = Field(
        default_factory=list, description="Must be empty when quality_gate is 'passed'"
    )

    final_deliverable_ready: bool
    preserved_limitations: List[str] = Field(
        default_factory=list,
        description="Limitations/insufficient-evidence flags carried forward verbatim from constituent agents — never dropped, never softened",
    )
    next_actions: List[str] = Field(default_factory=list, description="Concrete follow-ups, each tied to a specific open item")

    human_readable_summary: str = Field(..., description="Markdown summary of the session's overall state for a human reader")
    supervisor_confidence: ConfidenceLevel


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

_ORCHESTRATED_AGENT_IDS = [spec.id for spec in AGENT_REGISTRY]

SYSTEM_PROMPT = f"""\
You are the Supervisor Agent inside the AI Career Copilot, a multi-agent \
system. You are the top-level entry point: you do not analyze resumes, \
job descriptions, or companies yourself, and you do not write career \
content. You coordinate the Planner Agent's plan, what actually ran, and \
the Critic Agent's review, and you render a single go/no-go verdict on \
whether the package is ready to deliver to the user.

The only agents you may reference in `orchestration_log` are these real \
ids: {_ORCHESTRATED_AGENT_IDS}. Never invent an agent, and never omit one \
that's in this list — `orchestration_log` must have exactly one entry per \
id.

Non-negotiable rules:
1. Build `orchestration_log` by cross-checking the Planner's own \
`execution_plan` (parsed from `planner_output`) against \
`completed_agent_ids` and `failed_agent_ids`. An agent the plan marked \
'run' that shows up in `completed_agent_ids` is `ran`. An agent the plan \
marked 'skip' that never ran is `skipped_per_plan`. An agent the plan \
marked 'run' that is in neither `completed_agent_ids` nor \
`failed_agent_ids` is `planned_but_not_run` — a real discrepancy, not a \
detail to smooth over. An agent in `failed_agent_ids` is `failed`. An \
agent that ran but the plan never called for is `ran_but_not_planned` — \
also a discrepancy worth surfacing, even if the extra output is harmless.
2. Every discrepancy status (`planned_but_not_run`, `ran_but_not_planned`, \
`failed`) must produce a corresponding entry in `plan_adherence_issues`. \
If there are none, leave it empty — do not invent one to have something \
to report.
3. Build `issue_resolutions` from every `major` or `critical` severity \
issue inside `critic_output`'s `agent_reviews[*].issues_found` (if \
`critic_output` was provided). Mark an issue `resolved` ONLY if \
`post_critic_fixes_applied` contains a description that plausibly \
addresses that specific issue — never mark something resolved on the \
strength of a general assurance. If no matching fix is named, it is \
`unresolved`. If `critic_output` was not provided at all, do not silently \
treat the system as clean — say explicitly in `preserved_limitations` \
that quality could not be independently verified this session, and let \
that drive `quality_gate` downward.
4. `quality_gate` follows strictly from `issue_resolutions` and \
`plan_adherence_issues`, never from a general vibe:
   - `blocked`: any unresolved critical issue, or any `failed`/\
`planned_but_not_run` status on an agent needed for the user's stated \
goal.
   - `held_for_revision`: any unresolved major issue, with no unresolved \
criticals.
   - `passed_with_notes`: all major/critical issues resolved, but minor \
or suggestion-level issues remain open, or minor plan-adherence notes \
exist.
   - `passed`: no unresolved issues of any severity and no plan-adherence \
issues.
5. `final_deliverable_ready` is true only when `quality_gate` is `passed` \
or `passed_with_notes` AND `session_status` is not `blocked`. Set it to \
false otherwise, even if most of the system looks fine — one real \
blocking problem is enough.
6. `preserved_limitations` must carry forward, not paraphrase away, the \
actual `limitations` lists from `critic_output` and `final_report_output` \
where relevant, plus anything from `planner_output`'s own limitations \
that still applies (e.g. an assumption the plan made that hasn't been \
independently checked). Never drop a limitation because it's inconvenient \
to the verdict you're about to render.
7. `next_actions` must be concrete and tied to a specific open item — \
"fix X's total_estimated_time field to match its own line items", not \
"review outputs for quality."
8. Set `supervisor_confidence` based on how much you actually had to \
verify against (full critic_output vs. none, complete vs. partial \
completed_agent_ids), and say why in `human_readable_summary` if \
confidence is anything less than high.

Output ONLY through the provided tool call. Do not add commentary outside it.\
"""


class SupervisorAgent(BaseAgent[SupervisorInput, SupervisorOutput]):
    name = "Supervisor Agent"
    system_prompt = SYSTEM_PROMPT
    input_model = SupervisorInput
    output_model = SupervisorOutput

    def build_user_prompt(self, data: SupervisorInput) -> str:
        registry_block = "\n".join(f"- {spec.id}" for spec in AGENT_REGISTRY)

        header = (
            f"Candidate: {data.candidate_name}\n"
            f"Target role: {data.target_role}\n"
            f"Company: {data.company_name or 'not specified'}\n"
            f"User goal (their own words): {data.user_goal}\n\n"
            f"Completed agent ids: {data.completed_agent_ids or 'none'}\n"
            f"Failed agent ids: {data.failed_agent_ids or 'none'}\n"
            f"Post-critic fixes applied: {data.post_critic_fixes_applied or 'none'}\n"
        )

        blocks = [
            "--- AGENT_REGISTRY (all ids you must cover in orchestration_log) START ---",
            registry_block,
            "--- AGENT_REGISTRY END ---",
            "",
            "--- PLANNER_OUTPUT START ---",
            data.planner_output,
            "--- PLANNER_OUTPUT END ---",
        ]
        if data.critic_output:
            blocks += ["", "--- CRITIC_OUTPUT START ---", data.critic_output, "--- CRITIC_OUTPUT END ---"]
        else:
            blocks += ["", "(No critic_output was provided this session.)"]
        if data.final_report_output:
            blocks += ["", "--- FINAL_REPORT_OUTPUT START ---", data.final_report_output, "--- FINAL_REPORT_OUTPUT END ---"]

        return header + "\n" + "\n".join(blocks) + (
            "\n\nProduce the full supervision verdict per your instructions: an orchestration_log "
            "entry for every registry agent, issue_resolutions for every major/critical Critic "
            "finding, and a quality_gate that follows strictly from what you actually found."
        )
