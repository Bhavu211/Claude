"""Summary metric cards shown at the top of the dashboard."""

from __future__ import annotations

import streamlit as st

from dashboard import db


def compute_stats(db_path: str = db.DEFAULT_DB_PATH) -> dict:
    apps = db.list_applications(db_path=db_path)
    companies = db.list_companies(db_path=db_path)
    resumes = db.list_resume_versions(db_path=db_path)

    completed = [a for a in apps if a["status"] == "completed"]
    ats_scores = [a["ats_score"] for a in completed if a["ats_score"] is not None]
    ready = [a for a in completed if a.get("interview_readiness") == "ready"]

    return {
        "total_applications": len(apps),
        "companies_analyzed": len(companies),
        "resume_versions_created": len(resumes),
        "average_ats_score": round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else None,
        "interviews_generated": len(completed),
        "success_rate": round(100 * len(ready) / len(completed), 1) if completed else None,
    }


def render_summary_cards(db_path: str = db.DEFAULT_DB_PATH) -> None:
    stats = compute_stats(db_path)
    cols = st.columns(6)
    cols[0].metric("Total Applications", stats["total_applications"])
    cols[1].metric("Companies Analyzed", stats["companies_analyzed"])
    cols[2].metric("Resume Versions", stats["resume_versions_created"])
    cols[3].metric("Avg ATS Score", stats["average_ats_score"] if stats["average_ats_score"] is not None else "—")
    cols[4].metric("Interviews Generated", stats["interviews_generated"])
    cols[5].metric("Success Rate", f"{stats['success_rate']}%" if stats["success_rate"] is not None else "—")
