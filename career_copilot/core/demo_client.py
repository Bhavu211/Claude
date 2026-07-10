"""A drop-in LLMClient that replays this project's own verified
outputs/*_sample_output.json fixtures instead of calling the real API.

Every agent already accepts an optional `client` in its constructor
(`AgentCls(client=...)`), so demo mode is just "construct every agent with
a DemoLLMClient instead of a real LLMClient" — no monkeypatching of the
LLMClient class globally. That distinction matters in a long-lived,
multi-session server process (like the dashboard): patching the class
would leak into every concurrent user's session, while an instance swap
is fully isolated per request.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Type, TypeVar

from pydantic import BaseModel

from career_copilot.core.llm_client import LLMClient, LLMError

T = TypeVar("T", bound=BaseModel)

# output_model class name -> sample fixture filename under outputs/
SAMPLE_FILES = {
    "ResumeAnalysisOutput": "resume_analysis_sample_output.json",
    "JDIntelligenceOutput": "jd_intelligence_sample_output.json",
    "CompanyIntelligenceOutput": "company_intelligence_sample_output.json",
    "ATSOptimizationOutput": "ats_optimization_sample_output.json",
    "ResumeRewriteOutput": "resume_rewrite_sample_output.json",
    "GapAnalysisOutput": "gap_analysis_sample_output.json",
    "SkillEvidenceOutput": "skill_evidence_sample_output.json",
    "RecruiterSimulationOutput": "recruiter_simulation_sample_output.json",
    "PortfolioRecommendationOutput": "portfolio_recommendation_sample_output.json",
    "LearningCertificationOutput": "learning_certification_sample_output.json",
    "InterviewCoachOutput": "interview_coach_sample_output.json",
    "LinkedInOptimizationOutput": "linkedin_optimization_sample_output.json",
    "ApplicationAssetsOutput": "application_assets_sample_output.json",
    "CareerStrategyOutput": "career_strategy_sample_output.json",
    "FinalReportOutput": "final_report_sample_output.json",
    "PlannerOutput": "planner_sample_output.json",
    "CriticOutput": "critic_sample_output.json",
    "SupervisorOutput": "supervisor_sample_output.json",
}


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


def _approx_tokens(text: str) -> int:
    """Rough chars/4 estimate — good enough for demo-mode cost display,
    explicitly labeled as approximate everywhere it's shown."""
    return max(1, len(text) // 4)


class DemoLLMClient(LLMClient):
    """Deterministically replays this project's own hand-verified sample
    outputs. Never calls the network, never needs ANTHROPIC_API_KEY."""

    def __init__(self, outputs_dir: str = "outputs", delay_seconds: float = 0.0):
        super().__init__()
        self.outputs_dir = outputs_dir
        self.delay_seconds = delay_seconds

    def run_structured(self, *, system: str, user: str, output_model: Type[T]) -> T:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        filename = SAMPLE_FILES.get(output_model.__name__)
        if filename is None:
            raise LLMError(f"DemoLLMClient has no fixture registered for {output_model.__name__}")
        path = os.path.join(self.outputs_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = output_model.model_validate(data)
        self._record_usage(
            method="run_structured (demo, approximate)",
            usage=_FakeUsage(input_tokens=_approx_tokens(system + user), output_tokens=_approx_tokens(json.dumps(data))),
        )
        return result

    def run_with_web_search(self, *, system: str, user: str, max_uses: int = 8) -> str:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        text = (
            "(Demo mode: no live web search was performed. The structuring pass that "
            "follows replays this project's own verified sample research instead.)"
        )
        self._record_usage(
            method="run_with_web_search (demo, approximate)",
            usage=_FakeUsage(input_tokens=_approx_tokens(system + user), output_tokens=_approx_tokens(text)),
        )
        return text
