"""Run a single agent from the command line against one or more text files.

Usage:
    python -m career_copilot.cli resume_analysis samples/sample_resume.txt
    python -m career_copilot.cli gap_analysis samples/sample_resume.txt samples/sample_jd.txt

Each agent declares how many file arguments it needs and which input field
each one fills, in order — see AGENTS below. Agents whose input isn't
"one or more documents" (e.g. portfolio_recommendation, which takes a
structured list of gaps rather than a file) aren't reachable from this CLI;
use the Python API directly for those (see README).

Requires ANTHROPIC_API_KEY to be set (see README). Writes JSON output to
stdout.
"""

from __future__ import annotations

import sys

from career_copilot.agents.resume_analysis import ResumeAnalysisAgent, ResumeAnalysisInput
from career_copilot.agents.jd_intelligence import JDIntelligenceAgent, JDIntelligenceInput
from career_copilot.agents.company_intelligence import CompanyIntelligenceAgent, CompanyIntelligenceInput
from career_copilot.agents.ats_optimization import ATSOptimizationAgent, ATSOptimizationInput
from career_copilot.agents.resume_rewrite import ResumeRewriteAgent, ResumeRewriteInput
from career_copilot.agents.gap_analysis import GapAnalysisAgent, GapAnalysisInput
from career_copilot.agents.skill_evidence import SkillEvidenceAgent, SkillEvidenceInput
from career_copilot.agents.recruiter_simulation import RecruiterSimulationAgent, RecruiterSimulationInput
from career_copilot.agents.interview_coach import InterviewCoachAgent, InterviewCoachInput
from career_copilot.agents.linkedin_optimization import LinkedInOptimizationAgent, LinkedInOptimizationInput
from career_copilot.agents.application_assets import ApplicationAssetsAgent, ApplicationAssetsInput

# agent_key -> (agent_cls, input_cls, field_names)
# field_names is an ordered tuple of input fields, one per file argument.
# Fields not listed here (e.g. optional context fields) simply aren't set
# from the CLI — use the Python API if you need them.
AGENTS = {
    "resume_analysis": (ResumeAnalysisAgent, ResumeAnalysisInput, ("resume_text",)),
    "jd_intelligence": (JDIntelligenceAgent, JDIntelligenceInput, ("jd_text",)),
    # company_intelligence takes a plain company name, not a document — the
    # file's stripped content becomes company_name.
    "company_intelligence": (CompanyIntelligenceAgent, CompanyIntelligenceInput, ("company_name",)),
    "ats_optimization": (ATSOptimizationAgent, ATSOptimizationInput, ("resume_text", "jd_text")),
    "resume_rewrite": (ResumeRewriteAgent, ResumeRewriteInput, ("resume_text", "jd_text")),
    "gap_analysis": (GapAnalysisAgent, GapAnalysisInput, ("resume_text", "jd_text")),
    "skill_evidence": (SkillEvidenceAgent, SkillEvidenceInput, ("resume_text", "jd_text")),
    "recruiter_simulation": (RecruiterSimulationAgent, RecruiterSimulationInput, ("resume_text", "jd_text")),
    "interview_coach": (InterviewCoachAgent, InterviewCoachInput, ("resume_text", "jd_text")),
    "linkedin_optimization": (LinkedInOptimizationAgent, LinkedInOptimizationInput, ("resume_text", "jd_text")),
    "application_assets": (ApplicationAssetsAgent, ApplicationAssetsInput, ("resume_text", "jd_text")),
    # portfolio_recommendation and learning_certification are intentionally
    # absent: their required input (gaps_to_close, a list) isn't a document
    # to read from a file.
}


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: python -m career_copilot.cli <{'|'.join(AGENTS)}> <file1> [file2 ...]", file=sys.stderr)
        raise SystemExit(1)

    agent_key, file_paths = sys.argv[1], sys.argv[2:]
    if agent_key not in AGENTS:
        print(f"Unknown agent '{agent_key}'. Choices: {', '.join(AGENTS)}", file=sys.stderr)
        raise SystemExit(1)

    agent_cls, input_cls, field_names = AGENTS[agent_key]
    if len(file_paths) != len(field_names):
        print(
            f"'{agent_key}' needs {len(field_names)} file argument(s) ({', '.join(field_names)}), "
            f"got {len(file_paths)}.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    kwargs = {}
    for field_name, path in zip(field_names, file_paths):
        with open(path, "r", encoding="utf-8") as f:
            kwargs[field_name] = f.read()

    agent = agent_cls()
    result = agent.run(input_cls(**kwargs))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
