"""The system's single top-to-bottom entry point.

`run_pipeline()` is what the 18 agents were actually built to compose into:
it runs Planner Agent to decide what to do, executes every specialist agent
the plan calls for in real dependency order (topologically sorted from
`AGENT_REGISTRY`, not a hardcoded sequence), wires each agent's *real*
required fields from the actual outputs of the agents it depends on (not
just raw resume/JD text), runs Final Report once everything upstream is
done, then hands the whole session to Critic Agent for review and
Supervisor Agent for the final go/no-go verdict.

This module contains no career-content logic of its own — every judgment
call belongs to the agent whose job it is; this only wires them together
correctly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.registry import AGENT_REGISTRY, AGENT_BY_ID

if TYPE_CHECKING:
    from career_copilot.core.run_log import RunLogger
    from career_copilot.core.llm_client import LLMClient
from career_copilot.agents.planner import PlannerAgent, PlannerInput, PlannerOutput
from career_copilot.agents.critic import CriticAgent, CriticInput, CriticOutput
from career_copilot.agents.supervisor import SupervisorAgent, SupervisorInput, SupervisorOutput

from career_copilot.agents.resume_analysis import ResumeAnalysisAgent, ResumeAnalysisInput
from career_copilot.agents.jd_intelligence import JDIntelligenceAgent, JDIntelligenceInput
from career_copilot.agents.company_intelligence import CompanyIntelligenceAgent, CompanyIntelligenceInput
from career_copilot.agents.ats_optimization import ATSOptimizationAgent, ATSOptimizationInput
from career_copilot.agents.resume_rewrite import ResumeRewriteAgent, ResumeRewriteInput
from career_copilot.agents.gap_analysis import GapAnalysisAgent, GapAnalysisInput
from career_copilot.agents.skill_evidence import SkillEvidenceAgent, SkillEvidenceInput
from career_copilot.agents.recruiter_simulation import RecruiterSimulationAgent, RecruiterSimulationInput
from career_copilot.agents.portfolio_recommendation import PortfolioRecommendationAgent, PortfolioRecommendationInput
from career_copilot.agents.learning_certification import LearningCertificationAgent, LearningCertificationInput
from career_copilot.agents.interview_coach import InterviewCoachAgent, InterviewCoachInput
from career_copilot.agents.linkedin_optimization import LinkedInOptimizationAgent, LinkedInOptimizationInput
from career_copilot.agents.application_assets import ApplicationAssetsAgent, ApplicationAssetsInput
from career_copilot.agents.career_strategy import CareerStrategyAgent, CareerStrategyInput
from career_copilot.agents.final_report import FinalReportAgent, FinalReportInput

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class PipelineInput(BaseModel):
    candidate_name: str
    target_role: str
    resume_text: str
    jd_text: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    user_goal: str = Field(..., description="The user's own words describing what they want")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class PipelineResult(BaseModel):
    planner_output: PlannerOutput
    agent_outputs: Dict[str, dict] = Field(..., description="agent_id -> that agent's raw output dict")
    critic_output: Optional[CriticOutput] = None
    supervisor_output: Optional[SupervisorOutput] = None


class ExecutionEvent(BaseModel):
    """One step of a run_pipeline() call, emitted to an optional `on_event`
    callback so a caller (e.g. a live dashboard) can render progress without
    duplicating any orchestration logic."""

    event_type: str = Field(
        ..., description="'plan_ready' | 'agent_started' | 'agent_completed' | 'agent_failed' | "
        "'critic_started' | 'critic_completed' | 'supervisor_started' | 'supervisor_completed' | 'pipeline_completed'"
    )
    agent_id: Optional[str] = None
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    run_order: Optional[List[str]] = Field(default=None, description="Set only on 'plan_ready'")
    error: Optional[str] = Field(default=None, description="Set only on 'agent_failed'")


def _emit(on_event: Optional[Callable[[ExecutionEvent], None]], **kwargs) -> None:
    if on_event is not None:
        on_event(ExecutionEvent(**kwargs))


# ---------------------------------------------------------------------------
# Agent registry -> (agent_cls, input_cls)
# ---------------------------------------------------------------------------

_AGENT_CLASSES = {
    "resume_analysis": (ResumeAnalysisAgent, ResumeAnalysisInput),
    "jd_intelligence": (JDIntelligenceAgent, JDIntelligenceInput),
    "company_intelligence": (CompanyIntelligenceAgent, CompanyIntelligenceInput),
    "ats_optimization": (ATSOptimizationAgent, ATSOptimizationInput),
    "resume_rewrite": (ResumeRewriteAgent, ResumeRewriteInput),
    "gap_analysis": (GapAnalysisAgent, GapAnalysisInput),
    "skill_evidence": (SkillEvidenceAgent, SkillEvidenceInput),
    "recruiter_simulation": (RecruiterSimulationAgent, RecruiterSimulationInput),
    "portfolio_recommendation": (PortfolioRecommendationAgent, PortfolioRecommendationInput),
    "learning_certification": (LearningCertificationAgent, LearningCertificationInput),
    "interview_coach": (InterviewCoachAgent, InterviewCoachInput),
    "linkedin_optimization": (LinkedInOptimizationAgent, LinkedInOptimizationInput),
    "application_assets": (ApplicationAssetsAgent, ApplicationAssetsInput),
    "career_strategy": (CareerStrategyAgent, CareerStrategyInput),
    "final_report": (FinalReportAgent, FinalReportInput),
}
assert set(_AGENT_CLASSES) == {spec.id for spec in AGENT_REGISTRY}


def _topological_order(agent_ids: List[str]) -> List[str]:
    """Order agent_ids so every agent runs after everything in its `depends_on`
    that's also in this run, per AGENT_REGISTRY — never a hardcoded sequence."""
    remaining = set(agent_ids)
    ordered: List[str] = []
    while remaining:
        ready = sorted(
            aid for aid in remaining
            if not (set(AGENT_BY_ID[aid].depends_on) & remaining)
        )
        if not ready:
            raise ValueError(f"Dependency cycle among: {remaining}")
        ordered.extend(ready)
        remaining -= set(ready)
    return ordered


def _summary(outputs: Dict[str, BaseModel], agent_id: str) -> Optional[str]:
    out = outputs.get(agent_id)
    return getattr(out, "human_readable_summary", None) if out else None


def _build_input(agent_id: str, data: PipelineInput, outputs: Dict[str, BaseModel]) -> BaseModel:
    """Build the given agent's real input model from the pipeline's raw data
    plus whatever upstream agents in `outputs` have already produced."""

    if agent_id == "resume_analysis":
        return ResumeAnalysisInput(resume_text=data.resume_text, candidate_name=data.candidate_name)

    if agent_id == "jd_intelligence":
        if not data.jd_text:
            raise ValueError("jd_intelligence requires jd_text")
        return JDIntelligenceInput(jd_text=data.jd_text, company_name=data.company_name, role_title=data.target_role)

    if agent_id == "company_intelligence":
        if not data.company_name:
            raise ValueError("company_intelligence requires company_name")
        return CompanyIntelligenceInput(company_name=data.company_name, target_role=data.target_role)

    if agent_id == "ats_optimization":
        return ATSOptimizationInput(resume_text=data.resume_text, jd_text=data.jd_text, target_role=data.target_role)

    if agent_id == "resume_rewrite":
        return ResumeRewriteInput(
            resume_text=data.resume_text, jd_text=data.jd_text,
            target_role=data.target_role, company_name=data.company_name,
        )

    if agent_id == "gap_analysis":
        if not data.jd_text:
            raise ValueError("gap_analysis requires jd_text")
        return GapAnalysisInput(resume_text=data.resume_text, jd_text=data.jd_text)

    if agent_id == "skill_evidence":
        if not data.jd_text:
            raise ValueError("skill_evidence requires jd_text")
        return SkillEvidenceInput(resume_text=data.resume_text, jd_text=data.jd_text)

    if agent_id == "recruiter_simulation":
        if not data.jd_text:
            raise ValueError("recruiter_simulation requires jd_text")
        return RecruiterSimulationInput(resume_text=data.resume_text, jd_text=data.jd_text, company_name=data.company_name)

    if agent_id == "portfolio_recommendation":
        # gaps_to_close is real structured output, not re-derived text — the
        # whole point of this agent being "synthesis" not "extraction".
        gaps: List[str] = []
        gap_out = outputs.get("gap_analysis")
        if gap_out is not None:
            gaps.extend(gap_out.critical_gaps)
        skill_out = outputs.get("skill_evidence")
        if skill_out is not None:
            gaps.extend(g for g in skill_out.weakly_evidenced_skills if g not in gaps)
        if not gaps:
            raise ValueError("portfolio_recommendation needs gaps_to_close from gap_analysis/skill_evidence output")
        return PortfolioRecommendationInput(
            target_role=data.target_role, company_name=data.company_name, gaps_to_close=gaps,
        )

    if agent_id == "learning_certification":
        competencies: List[str] = []
        gap_out = outputs.get("gap_analysis")
        if gap_out is not None:
            competencies.extend(gap_out.critical_gaps)
        skill_out = outputs.get("skill_evidence")
        if skill_out is not None:
            competencies.extend(g for g in skill_out.weakly_evidenced_skills if g not in competencies)
        if not competencies:
            raise ValueError("learning_certification needs missing_competencies from gap_analysis/skill_evidence output")
        return LearningCertificationInput(
            target_role=data.target_role, company_name=data.company_name, missing_competencies=competencies,
        )

    if agent_id == "interview_coach":
        if not data.jd_text:
            raise ValueError("interview_coach requires jd_text")
        company_out = outputs.get("company_intelligence")
        return InterviewCoachInput(
            resume_text=data.resume_text, jd_text=data.jd_text, company_name=data.company_name,
            company_context=_summary(outputs, "company_intelligence") if company_out else None,
        )

    if agent_id == "linkedin_optimization":
        titles: List[str] = []
        portfolio_out = outputs.get("portfolio_recommendation")
        if portfolio_out is not None:
            titles = [p.title for p in portfolio_out.projects]
        return LinkedInOptimizationInput(
            resume_text=data.resume_text, jd_text=data.jd_text, target_role=data.target_role,
            company_name=data.company_name, portfolio_project_titles=titles,
        )

    if agent_id == "application_assets":
        return ApplicationAssetsInput(
            resume_text=data.resume_text, jd_text=data.jd_text, target_role=data.target_role,
            company_name=data.company_name, company_context=_summary(outputs, "company_intelligence"),
        )

    if agent_id == "career_strategy":
        key_findings = " ".join(
            s for s in (
                _summary(outputs, "gap_analysis"), _summary(outputs, "skill_evidence"),
                _summary(outputs, "recruiter_simulation"),
            ) if s
        ) or None
        plan_summary = " ".join(
            s for s in (
                _summary(outputs, "portfolio_recommendation"), _summary(outputs, "learning_certification"),
            ) if s
        ) or None
        return CareerStrategyInput(
            resume_text=data.resume_text, target_role=data.target_role, company_name=data.company_name,
            location=data.location, key_findings_summary=key_findings,
            portfolio_and_learning_plan_summary=plan_summary,
        )

    if agent_id == "final_report":
        ats_out = outputs.get("ats_optimization")
        gap_out = outputs.get("gap_analysis")
        recruiter_out = outputs.get("recruiter_simulation")
        strategy_out = outputs.get("career_strategy")

        gap_stats = None
        if gap_out is not None:
            gap_stats = (
                f"{len(gap_out.rows)} requirements assessed; "
                f"{len(gap_out.critical_gaps)} critical gap(s); "
                f"{len(gap_out.strongest_matches)} strongest match(es)."
            )
        salary_range = None
        if strategy_out is not None:
            s = strategy_out.market_salary_estimate
            salary_range = f"{s.range_low}-{s.range_high} {s.currency_and_period}"

        return FinalReportInput(
            candidate_name=data.candidate_name, target_role=data.target_role, company_name=data.company_name,
            resume_analysis_summary=_summary(outputs, "resume_analysis"),
            jd_intelligence_summary=_summary(outputs, "jd_intelligence"),
            company_intelligence_summary=_summary(outputs, "company_intelligence"),
            ats_optimization_summary=_summary(outputs, "ats_optimization"),
            resume_rewrite_summary=_summary(outputs, "resume_rewrite"),
            gap_analysis_summary=_summary(outputs, "gap_analysis"),
            skill_evidence_summary=_summary(outputs, "skill_evidence"),
            portfolio_recommendation_summary=_summary(outputs, "portfolio_recommendation"),
            learning_certification_summary=_summary(outputs, "learning_certification"),
            recruiter_simulation_summary=_summary(outputs, "recruiter_simulation"),
            interview_coach_summary=_summary(outputs, "interview_coach"),
            linkedin_optimization_summary=_summary(outputs, "linkedin_optimization"),
            application_assets_summary=_summary(outputs, "application_assets"),
            career_strategy_summary=_summary(outputs, "career_strategy"),
            ats_score=ats_out.ats_compatibility_score if ats_out else None,
            gap_analysis_stats=gap_stats,
            recruiter_recommendation=recruiter_out.hiring_recommendation.value if recruiter_out else None,
            role_fit=strategy_out.role_fit_assessment.value if strategy_out else None,
            salary_range=salary_range,
        )

    raise ValueError(f"No input builder registered for agent_id={agent_id!r}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_pipeline(
    data: PipelineInput,
    logger: Optional["RunLogger"] = None,
    on_event: Optional[Callable[[ExecutionEvent], None]] = None,
    client_factory: Optional[Callable[[], "LLMClient"]] = None,
) -> PipelineResult:
    """Run the full 18-agent system.

    - `logger`: pass a `RunLogger` (career_copilot.core.run_log) to persist this
      run to SQLite — opt-in, never affects orchestration.
    - `on_event`: called with an `ExecutionEvent` at each step (plan ready, each
      agent started/completed/failed, critic/supervisor started/completed) — lets
      a caller (e.g. a live dashboard) render progress without reimplementing
      any orchestration logic.
    - `client_factory`: called with no args to build the `LLMClient` each agent
      uses. Defaults to each agent's own default (a real `LLMClient`). Pass
      `lambda: DemoLLMClient()` (career_copilot.core.demo_client) to replay this
      project's verified sample fixtures instead of calling the live API.

    A single agent failing does not abort the run — it's recorded as
    'agent_failed' and skipped; agents that hard-depend on its output will
    then also fail naturally when they can't find what they need, and are
    themselves recorded rather than raising out of this function. Planner,
    Critic, and Supervisor are still run at the end against whatever
    actually completed.
    """
    def _agent(agent_cls):
        return agent_cls(client=client_factory()) if client_factory else agent_cls()

    planner = _agent(PlannerAgent)
    plan = planner.run(PlannerInput(
        user_goal=data.user_goal,
        has_resume=bool(data.resume_text),
        has_jd=bool(data.jd_text),
        has_company_name=bool(data.company_name),
    ))

    run_ids = [item.agent_id for item in plan.execution_plan if item.action == "run"]
    order = _topological_order(run_ids)
    _emit(on_event, event_type="plan_ready", message=f"{len(order)} agent(s) planned to run", run_order=order)

    outputs: Dict[str, BaseModel] = {}
    failed_ids: List[str] = []
    for agent_id in order:
        agent_cls, _ = _AGENT_CLASSES[agent_id]
        _emit(on_event, event_type="agent_started", agent_id=agent_id, message=f"Running {agent_cls.__name__}")
        try:
            agent_input = _build_input(agent_id, data, outputs)
            outputs[agent_id] = _agent(agent_cls).run(agent_input)
            _emit(on_event, event_type="agent_completed", agent_id=agent_id, message="Completed")
        except Exception as exc:  # noqa: BLE001 — a failing agent must not abort the whole run
            failed_ids.append(agent_id)
            _emit(on_event, event_type="agent_failed", agent_id=agent_id, message="Failed", error=str(exc))

    critic_output = None
    if any(aid != "final_report" for aid in outputs):
        _emit(on_event, event_type="critic_started", message="Reviewing all completed agent outputs")
        critic = _agent(CriticAgent)
        critic_kwargs = {
            "resume_text": data.resume_text, "jd_text": data.jd_text, "company_name": data.company_name,
        }
        for aid, out in outputs.items():
            if aid == "final_report":
                continue
            critic_kwargs[f"{aid}_output"] = out.model_dump_json()
        critic_output = critic.run(CriticInput(**critic_kwargs))
        _emit(on_event, event_type="critic_completed", message="Review complete")

    _emit(on_event, event_type="supervisor_started", message="Rendering final verdict")
    supervisor = _agent(SupervisorAgent)
    supervisor_output = supervisor.run(SupervisorInput(
        candidate_name=data.candidate_name,
        target_role=data.target_role,
        company_name=data.company_name,
        user_goal=data.user_goal,
        planner_output=plan.model_dump_json(),
        completed_agent_ids=list(outputs.keys()),
        failed_agent_ids=failed_ids,
        critic_output=critic_output.model_dump_json() if critic_output else None,
        final_report_output=outputs["final_report"].model_dump_json() if "final_report" in outputs else None,
    ))
    _emit(on_event, event_type="supervisor_completed", message="Verdict ready")

    result = PipelineResult(
        planner_output=plan,
        agent_outputs={aid: out.model_dump() for aid, out in outputs.items()},
        critic_output=critic_output,
        supervisor_output=supervisor_output,
    )

    if logger is not None:
        logger.log_run(pipeline_input=data, result=result)

    _emit(on_event, event_type="pipeline_completed", message="Pipeline finished")
    return result
