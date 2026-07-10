"""SQLite persistence for the dashboard: applications, companies, resume
versions, and per-agent execution logs. Separate from career_copilot/core/run_log.py
(that module is pipeline-level, keyed by run; this one is dashboard-level,
keyed by application/company/resume-version, and is what every dashboard
page actually queries)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "dashboard/career_copilot_dashboard.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    industry TEXT,
    products TEXT,
    tech_stack TEXT,
    culture TEXT,
    recent_news TEXT,
    required_skills TEXT,
    last_researched_at TEXT
);

CREATE TABLE IF NOT EXISTS resume_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    file_path TEXT,
    content_hash TEXT NOT NULL,
    ats_score INTEGER,
    application_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_name TEXT,
    company_id INTEGER,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    resume_version_id INTEGER,
    years_of_experience TEXT,
    ats_score INTEGER,
    skills_missing TEXT,
    interview_readiness TEXT,
    quality_gate TEXT,
    status TEXT NOT NULL,
    output_folder TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    task TEXT,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    error TEXT
);
"""


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    parent = Path(db_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


def get_or_create_company(name: str, db_path: str = DEFAULT_DB_PATH) -> int:
    with closing(_conn(db_path)) as conn:
        row = conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO companies (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid


def update_company_research(
    name: str, *, industry: Optional[str] = None, products: Optional[List[str]] = None,
    tech_stack: Optional[List[str]] = None, culture: Optional[str] = None,
    recent_news: Optional[List[str]] = None, required_skills: Optional[List[str]] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    company_id = get_or_create_company(name, db_path)
    with closing(_conn(db_path)) as conn:
        conn.execute(
            """UPDATE companies SET industry = COALESCE(?, industry),
               products = COALESCE(?, products), tech_stack = COALESCE(?, tech_stack),
               culture = COALESCE(?, culture), recent_news = COALESCE(?, recent_news),
               required_skills = COALESCE(?, required_skills), last_researched_at = ?
               WHERE id = ?""",
            (
                industry, json.dumps(products) if products is not None else None,
                json.dumps(tech_stack) if tech_stack is not None else None, culture,
                json.dumps(recent_news) if recent_news is not None else None,
                json.dumps(required_skills) if required_skills is not None else None,
                _now(), company_id,
            ),
        )
        conn.commit()


def list_companies(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    with closing(_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM companies ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_company_application_count(company_name: str, db_path: str = DEFAULT_DB_PATH) -> int:
    with closing(_conn(db_path)) as conn:
        row = conn.execute(
            "SELECT COUNT(*) as n FROM applications WHERE company_name = ?", (company_name,)
        ).fetchone()
    return row["n"] if row else 0


# ---------------------------------------------------------------------------
# Resume versions
# ---------------------------------------------------------------------------


def insert_resume_version(
    label: str, content_hash: str, *, file_path: Optional[str] = None,
    ats_score: Optional[int] = None, application_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    with closing(_conn(db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO resume_versions (label, file_path, content_hash, ats_score, application_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (label, file_path, content_hash, ats_score, application_id, _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_resume_versions(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    with closing(_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM resume_versions ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------


def create_application(
    *, candidate_name: str, company_name: str, job_title: str,
    years_of_experience: Optional[str] = None, resume_version_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    company_id = get_or_create_company(company_name, db_path)
    with closing(_conn(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO applications
               (candidate_name, company_id, company_name, job_title, resume_version_id,
                years_of_experience, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'running', ?)""",
            (candidate_name, company_id, company_name, job_title, resume_version_id, years_of_experience, _now()),
        )
        conn.commit()
        return cur.lastrowid


def complete_application(
    application_id: int, *, ats_score: Optional[int], skills_missing: List[str],
    interview_readiness: Optional[str], quality_gate: Optional[str], status: str,
    output_folder: Optional[str], db_path: str = DEFAULT_DB_PATH,
) -> None:
    with closing(_conn(db_path)) as conn:
        conn.execute(
            """UPDATE applications SET ats_score = ?, skills_missing = ?, interview_readiness = ?,
               quality_gate = ?, status = ?, output_folder = ? WHERE id = ?""",
            (ats_score, json.dumps(skills_missing), interview_readiness, quality_gate, status, output_folder, application_id),
        )
        conn.commit()


def list_applications(
    *, company_name: Optional[str] = None, status: Optional[str] = None, db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM applications"
    conditions, params = [], []
    if company_name:
        conditions.append("company_name = ?")
        params.append(company_name)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"
    with closing(_conn(db_path)) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_application(application_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    with closing(_conn(db_path)) as conn:
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Execution logs
# ---------------------------------------------------------------------------


def insert_execution_log(
    application_id: int, agent_id: str, status: str, *, task: str = "",
    started_at: Optional[str] = None, finished_at: Optional[str] = None,
    duration_ms: Optional[int] = None, error: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    with closing(_conn(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO execution_logs
               (application_id, agent_id, status, task, started_at, finished_at, duration_ms, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (application_id, agent_id, status, task, started_at, finished_at, duration_ms, error),
        )
        conn.commit()
        return cur.lastrowid


def list_execution_logs(application_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    with closing(_conn(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM execution_logs WHERE application_id = ? ORDER BY id", (application_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


_EXPORTABLE_TABLES = {"applications", "companies", "resume_versions", "execution_logs"}


def _read_table(table: str, db_path: str):
    import pandas as pd
    if table not in _EXPORTABLE_TABLES:
        raise ValueError(f"Unknown table {table!r}; must be one of {_EXPORTABLE_TABLES}")
    with closing(_conn(db_path)) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)  # noqa: S608 — table checked against a fixed whitelist above


def export_table_csv(table: str, out_path: str, db_path: str = DEFAULT_DB_PATH) -> str:
    _read_table(table, db_path).to_csv(out_path, index=False)
    return out_path


def export_table_excel(table: str, out_path: str, db_path: str = DEFAULT_DB_PATH) -> str:
    _read_table(table, db_path).to_excel(out_path, index=False)
    return out_path
