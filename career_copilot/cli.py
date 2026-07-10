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

AGENTS = {
    "resume_analysis": (ResumeAnalysisAgent, ResumeAnalysisInput, "resume_text"),
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
