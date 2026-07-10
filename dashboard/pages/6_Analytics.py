from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import db

st.set_page_config(page_title="Analytics — Career Copilot", page_icon="📊", layout="wide")
db.init_db()

st.title("📊 Analytics")

apps = db.list_applications()
if not apps:
    st.info("No applications yet — analytics will populate once you run analyses.")
    st.stop()

df = pd.DataFrame(apps)
df["created_at"] = pd.to_datetime(df["created_at"])
df["month"] = df["created_at"].dt.strftime("%Y-%m")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Applications by month")
    by_month = df.groupby("month").size().reset_index(name="count")
    fig_month = px.bar(by_month, x="month", y="count")
    fig_month.update_xaxes(type="category")
    st.plotly_chart(fig_month, use_container_width=True)

with col2:
    st.subheader("Most applied companies")
    by_company = df["company_name"].value_counts().reset_index()
    by_company.columns = ["company", "applications"]
    st.plotly_chart(px.bar(by_company.head(10), x="company", y="applications"), use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("ATS score trend")
    scored = df.dropna(subset=["ats_score"]).sort_values("created_at")
    if len(scored) >= 1:
        st.plotly_chart(px.line(scored, x="created_at", y="ats_score", markers=True), use_container_width=True)
    else:
        st.caption("No scored applications yet.")

with col4:
    st.subheader("Most targeted industries")
    companies = {c["name"]: c["industry"] for c in db.list_companies() if c["industry"]}
    df["industry"] = df["company_name"].map(companies)
    industry_counts = df.dropna(subset=["industry"])["industry"].value_counts().reset_index()
    industry_counts.columns = ["industry", "applications"]
    if len(industry_counts):
        st.plotly_chart(px.pie(industry_counts, names="industry", values="applications"), use_container_width=True)
    else:
        st.caption("No industry data yet — run Company Intelligence via a live pipeline run.")

st.subheader("Most common missing skills")
skill_counter = Counter()
for a in apps:
    if a.get("skills_missing"):
        for s in json.loads(a["skills_missing"]):
            skill_counter[s] += 1
if skill_counter:
    top = pd.DataFrame(skill_counter.most_common(10), columns=["skill", "count"])
    st.plotly_chart(px.bar(top, x="skill", y="count"), use_container_width=True)
else:
    st.caption("No skill-gap data recorded yet.")

st.subheader("Resume improvement over time (ATS score by resume version)")
versions = pd.DataFrame(db.list_resume_versions())
if len(versions) and versions["ats_score"].notna().any():
    versions["created_at"] = pd.to_datetime(versions["created_at"])
    versions = versions.dropna(subset=["ats_score"]).sort_values("created_at")
    st.plotly_chart(px.line(versions, x="created_at", y="ats_score", hover_name="label", markers=True), use_container_width=True)
else:
    st.caption("No resume version ATS history yet.")
