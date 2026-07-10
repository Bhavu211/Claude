from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import db

st.set_page_config(page_title="History — Career Copilot", page_icon="🕘", layout="wide")
db.init_db()

st.title("🕘 History")
st.caption("Full per-agent execution log across every application.")

apps = db.list_applications()
if not apps:
    st.info("No applications yet.")
    st.stop()

labels = ["All applications"] + [f"#{a['id']} — {a['company_name']} / {a['job_title']}" for a in apps]
selected = st.selectbox("Application", labels)

if selected == "All applications":
    all_logs = []
    for a in apps:
        for log in db.list_execution_logs(a["id"]):
            log["application"] = f"#{a['id']} {a['company_name']}/{a['job_title']}"
            all_logs.append(log)
    logs = all_logs
else:
    app = apps[labels.index(selected) - 1]
    logs = db.list_execution_logs(app["id"])
    for log in logs:
        log["application"] = selected

if not logs:
    st.info("No execution logs recorded for this selection.")
    st.stop()

df = pd.DataFrame(logs)
search = st.text_input("Search", placeholder="Filter by agent id, task, or error…")
if search:
    mask = df.apply(lambda row: search.lower() in " ".join(str(v) for v in row.values).lower(), axis=1)
    df = df[mask]

st.dataframe(df, use_container_width=True, hide_index=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("Export CSV"):
        path = db.export_table_csv("execution_logs", "dashboard/execution_logs_export.csv")
        st.success(f"Exported to `{path}`")
with col2:
    if st.button("Export Excel"):
        path = db.export_table_excel("execution_logs", "dashboard/execution_logs_export.xlsx")
        st.success(f"Exported to `{path}`")
