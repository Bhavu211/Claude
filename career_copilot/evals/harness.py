"""Eval harness scaffold: run an agent across a suite of hand-written test
cases (easy/normal/edge/bad-input/missing-information, per Phase 1 of the
project's validation plan) and score each with an LLM judge, tracking token
cost per case along the way.

This is scaffolding, not a finished eval suite — it provides the plumbing
(`run_eval_suite`) and the schema (`EvalCase`, `EvalResult`, `EvalReport`);
the actual 10-20 cases per agent still need to be written per-agent and, for
real numbers, run against a live `ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.registry import AGENT_BY_ID
from career_copilot.evals.judge import JudgeAgent, JudgeInput, JudgeVerdict

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class EvalCase(BaseModel):
    case_id: str
    category: str = Field(..., description="'easy' | 'normal' | 'edge' | 'bad_input' | 'missing_information'")
    description: str = Field(..., description="What this case is specifically checking for")
    input_kwargs: Dict[str, Any] = Field(..., description="Kwargs to construct the agent's input_model")


class EvalResult(BaseModel):
    case_id: str
    category: str
    ran_successfully: bool
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    verdict: Optional[JudgeVerdict] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class EvalReport(BaseModel):
    agent_id: str
    results: List[EvalResult]

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if not r.ran_successfully)

    @property
    def hallucination_count(self) -> int:
        return sum(1 for r in self.results if r.verdict and r.verdict.hallucination_detected)

    @property
    def mean_overall_score(self) -> Optional[float]:
        scores = [r.verdict.overall_score for r in self.results if r.verdict]
        return sum(scores) / len(scores) if scores else None

    @property
    def total_cost_usd(self) -> Optional[float]:
        costs = [r.estimated_cost_usd for r in self.results if r.estimated_cost_usd is not None]
        return sum(costs) if costs else None

    @property
    def total_tokens(self) -> int:
        return sum((r.input_tokens or 0) + (r.output_tokens or 0) for r in self.results)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def run_eval_case(
    agent: BaseAgent, case: EvalCase, judge: Optional[JudgeAgent] = None, agent_id: Optional[str] = None,
) -> EvalResult:
    """Run one test case against `agent`, then score it with `judge` (a fresh
    JudgeAgent() if not supplied). Never raises — a failing case produces an
    EvalResult with ran_successfully=False rather than aborting the suite.
    `agent_id` (an AGENT_REGISTRY key) is optional and only used to fetch a
    real description for the judge's context; falls back to `agent.name`."""
    usage_before = len(agent.client.usage_log)

    try:
        agent_input = agent.input_model(**case.input_kwargs)
        output = agent.run(agent_input)
    except Exception as exc:  # noqa: BLE001 — deliberately broad: a bad_input case is expected to sometimes fail
        return EvalResult(case_id=case.case_id, category=case.category, ran_successfully=False, error=str(exc))

    new_usage = agent.client.usage_log[usage_before:]
    input_tokens = sum(r.input_tokens for r in new_usage) or None
    output_tokens = sum(r.output_tokens for r in new_usage) or None
    costs = [r.estimated_cost_usd for r in new_usage]
    estimated_cost = sum(costs) if costs and all(c is not None for c in costs) else None

    verdict = None
    if judge is not None:
        registry_entry = AGENT_BY_ID.get(agent_id or "")
        agent_purpose = registry_entry.description if registry_entry else agent.name
        judge_verdict = judge.run(JudgeInput(
            agent_name=agent.name,
            agent_purpose=agent_purpose,
            case_category=case.category,
            case_description=case.description,
            input_summary=str(case.input_kwargs),
            output_json=output.model_dump_json(),
        ))
        verdict = judge_verdict

    return EvalResult(
        case_id=case.case_id,
        category=case.category,
        ran_successfully=True,
        output=output.model_dump(),
        verdict=verdict,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost,
    )


def run_eval_suite(agent_id: str, agent: BaseAgent, cases: List[EvalCase], judge: Optional[JudgeAgent] = None) -> EvalReport:
    judge = judge or JudgeAgent()
    results = [run_eval_case(agent, case, judge, agent_id=agent_id) for case in cases]
    return EvalReport(agent_id=agent_id, results=results)
