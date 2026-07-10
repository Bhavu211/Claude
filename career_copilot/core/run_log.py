"""Persists every pipeline run to SQLite so runs accumulate into real,
queryable history instead of being discarded after each call.

This is deliberately opt-in and separate from `pipeline.run_pipeline()`'s
core logic: pass a `RunLogger` to `run_pipeline()` to enable it, or use
`RunLogger.log_run()` directly against a `PipelineResult` you already have.
Nothing about agent orchestration depends on logging being enabled.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "career_copilot_runs.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    target_role TEXT NOT NULL,
    company_name TEXT,
    jd_snippet TEXT,
    resume_version_hash TEXT NOT NULL,
    ats_score INTEGER,
    skills_missing TEXT NOT NULL,
    interview_questions_count INTEGER,
    quality_gate TEXT,
    final_deliverable_ready INTEGER,
    completed_agent_ids TEXT NOT NULL,
    full_result_json TEXT NOT NULL
);
"""


@dataclass
class RunRecord:
    run_id: int
    run_at: str
    candidate_name: str
    target_role: str
    company_name: Optional[str]
    jd_snippet: Optional[str]
    resume_version_hash: str
    ats_score: Optional[int]
    skills_missing: List[str]
    interview_questions_count: Optional[int]
    quality_gate: Optional[str]
    final_deliverable_ready: Optional[bool]
    completed_agent_ids: List[str]


def _resume_version_hash(resume_text: str) -> str:
    """A short, stable fingerprint identifying a specific resume revision,
    so two runs against the same resume text are recognizably the same
    'version' without storing the full text as the version key."""
    return hashlib.sha256(resume_text.encode("utf-8")).hexdigest()[:12]


_INTERVIEW_QUESTION_FIELDS = (
    "hr_questions", "behavioral_questions", "technical_questions",
    "product_questions", "company_specific_questions",
)


def _interview_question_count(interview_out: Optional[Dict]) -> Optional[int]:
    if not interview_out:
        return None
    return sum(len(interview_out.get(field, [])) for field in _INTERVIEW_QUESTION_FIELDS)


class RunLogger:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True) if Path(db_path).parent != Path("") else None
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def log_run(self, *, pipeline_input: "Any", result: "Any") -> int:
        """Persist one `run_pipeline()` call. Accepts the actual
        `PipelineInput`/`PipelineResult` objects (typed as Any here to avoid
        a circular import with pipeline.py)."""
        ats_out = result.agent_outputs.get("ats_optimization")
        gap_out = result.agent_outputs.get("gap_analysis")
        skill_out = result.agent_outputs.get("skill_evidence")
        interview_out = result.agent_outputs.get("interview_coach")

        skills_missing: List[str] = []
        if gap_out:
            skills_missing.extend(gap_out.get("critical_gaps", []))
        if skill_out:
            for s in skill_out.get("weakly_evidenced_skills", []):
                if s not in skills_missing:
                    skills_missing.append(s)

        row = (
            datetime.now(timezone.utc).isoformat(),
            pipeline_input.candidate_name,
            pipeline_input.target_role,
            pipeline_input.company_name,
            (pipeline_input.jd_text or "")[:200] or None,
            _resume_version_hash(pipeline_input.resume_text),
            ats_out.get("ats_compatibility_score") if ats_out else None,
            json.dumps(skills_missing),
            _interview_question_count(interview_out),
            result.supervisor_output.quality_gate.value if result.supervisor_output else None,
            int(result.supervisor_output.final_deliverable_ready) if result.supervisor_output else None,
            json.dumps(list(result.agent_outputs.keys())),
            result.model_dump_json(),
        )

        with closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute(
                """INSERT INTO runs (
                    run_at, candidate_name, target_role, company_name, jd_snippet,
                    resume_version_hash, ats_score, skills_missing, interview_questions_count,
                    quality_gate, final_deliverable_ready, completed_agent_ids, full_result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                row,
            )
            conn.commit()
            return cur.lastrowid

    def query_runs(self, *, company_name: Optional[str] = None, limit: int = 50) -> List[RunRecord]:
        """Read back run history, most recent first. Filter by company_name
        to see every attempt against one employer over time."""
        query = "SELECT * FROM runs"
        params: tuple = ()
        if company_name:
            query += " WHERE company_name = ?"
            params = (company_name,)
        query += " ORDER BY run_at DESC LIMIT ?"
        params = params + (limit,)

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [
            RunRecord(
                run_id=r["run_id"],
                run_at=r["run_at"],
                candidate_name=r["candidate_name"],
                target_role=r["target_role"],
                company_name=r["company_name"],
                jd_snippet=r["jd_snippet"],
                resume_version_hash=r["resume_version_hash"],
                ats_score=r["ats_score"],
                skills_missing=json.loads(r["skills_missing"]),
                interview_questions_count=r["interview_questions_count"],
                quality_gate=r["quality_gate"],
                final_deliverable_ready=bool(r["final_deliverable_ready"]) if r["final_deliverable_ready"] is not None else None,
                completed_agent_ids=json.loads(r["completed_agent_ids"]),
            )
            for r in rows
        ]

    def get_full_result(self, run_id: int) -> Optional[Dict]:
        """Read back the complete PipelineResult JSON for one run."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT full_result_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None
