"""Run a single agent from the command line against a text file input.

Usage:
    python -m career_copilot.cli resume_analysis samples/sample_resume.txt

Requires ANTHROPIC_API_KEY to be set (see README). Writes JSON output to
stdout.
"""

from __future__ import annotations

import json
import sys

from career_copilot.agents.resume_analysis import ResumeAnalysisAgent, ResumeAnalysisInput
from career_copilot.agents.jd_intelligence import JDIntelligenceAgent, JDIntelligenceInput
from career_copilot.agents.company_intelligence import CompanyIntelligenceAgent, CompanyIntelligenceInput
from career_copilot.agents.ats_optimization import ATSOptimizationAgent, ATSOptimizationInput
from career_copilot.agents.resume_rewrite import ResumeRewriteAgent, ResumeRewriteInput

AGENTS = {
    "resume_analysis": (ResumeAnalysisAgent, ResumeAnalysisInput, "resume_text"),
    "jd_intelligence": (JDIntelligenceAgent, JDIntelligenceInput, "jd_text"),
    # company_intelligence takes a plain company name, not a document — the input
    # file's stripped content becomes company_name (see README for how to also
    # pass target_role via the Python API instead of this CLI).
    "company_intelligence": (CompanyIntelligenceAgent, CompanyIntelligenceInput, "company_name"),
    # ats_optimization and resume_rewrite also accept an optional jd_text — only
    # reachable via the Python API, not this single-file CLI.
    "ats_optimization": (ATSOptimizationAgent, ATSOptimizationInput, "resume_text"),
    "resume_rewrite": (ResumeRewriteAgent, ResumeRewriteInput, "resume_text"),
}


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: python -m career_copilot.cli <{'|'.join(AGENTS)}> <input_file>", file=sys.stderr)
        raise SystemExit(1)

    agent_key, input_path = sys.argv[1], sys.argv[2]
    if agent_key not in AGENTS:
        print(f"Unknown agent '{agent_key}'. Choices: {', '.join(AGENTS)}", file=sys.stderr)
        raise SystemExit(1)

    agent_cls, input_cls, text_field = AGENTS[agent_key]
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    agent = agent_cls()
    result = agent.run(input_cls(**{text_field: text}))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
