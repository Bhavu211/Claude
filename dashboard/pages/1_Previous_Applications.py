from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import db

st.set_page_config(page_title="Previous Applications — Career Copilot", page_icon="📂", layout="wide")
db.init_db()

st.title("📂 Previous Applications")

apps = db.list_applications()
if not apps:
    st.info("No applications yet — run one from **New Analysis**.")
    st.stop()

companies = sorted({a["company_name"] for a in apps})
col1, col2 = st.columns(2)
with col1:
    company_filter = st.selectbox("Filter by company", ["All"] + companies)
with col2:
    status_filter = st.selectbox("Filter by status", ["All", "completed", "running", "failed"])

filtered = apps
if company_filter != "All":
    filtered = [a for a in filtered if a["company_name"] == company_filter]
if status_filter != "All":
    filtered = [a for a in filtered if a["status"] == status_filter]

df = pd.DataFrame(filtered)[["id", "created_at", "candidate_name", "company_name", "job_title", "ats_score", "interview_readiness", "quality_gate", "status"]]
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Compare two applications")
if len(filtered) >= 2:
    ids = [f"#{a['id']} — {a['company_name']} / {a['job_title']}" for a in filtered]
    id_map = {label: a for label, a in zip(ids, filtered)}
    c1, c2 = st.columns(2)
    with c1:
        left_label = st.selectbox("Application A", ids, index=0)
    with c2:
        right_label = st.selectbox("Application B", ids, index=min(1, len(ids) - 1))
    left, right = id_map[left_label], id_map[right_label]
    cc1, cc2 = st.columns(2)
    for col, app in ((cc1, left), (cc2, right)):
        with col:
            st.markdown(f"**#{app['id']} — {app['company_name']} / {app['job_title']}**")
            st.metric("ATS Score", app["ats_score"] if app["ats_score"] is not None else "—")
            st.write(f"Quality gate: `{app['quality_gate']}`")
            st.write(f"Interview readiness: `{app['interview_readiness']}`")
            st.write(f"Output folder: `{app['output_folder']}`")
else:
    st.caption("Need at least 2 applications to compare.")
