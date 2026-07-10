from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import db

st.set_page_config(page_title="Resume Versions — Career Copilot", page_icon="📄", layout="wide")
db.init_db()

st.title("📄 Resume Versions")

versions = db.list_resume_versions()
if not versions:
    st.info("No resume versions yet — run an analysis from **New Analysis**.")
    st.stop()

df = pd.DataFrame(versions)[["id", "label", "content_hash", "ats_score", "created_at"]]
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("ATS score by resume version")
scored = [v for v in versions if v["ats_score"] is not None]
if scored:
    chart_df = pd.DataFrame(scored)[["label", "ats_score", "created_at"]].sort_values("created_at")
    st.bar_chart(chart_df.set_index("label")["ats_score"])
else:
    st.caption("No scored versions yet.")
