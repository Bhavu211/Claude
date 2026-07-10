"""Live activity console — filterable, searchable log of every agent event
in the current run."""

from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st


def render_console(log_rows: List[dict], key_prefix: str = "console") -> None:
    if not log_rows:
        st.caption("No activity yet.")
        return

    df = pd.DataFrame(log_rows)

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search logs", key=f"{key_prefix}_search", placeholder="Filter by agent, task, or message…")
    with col2:
        status_options = ["All"] + sorted(df["status"].dropna().unique().tolist())
        status_filter = st.selectbox("Status", status_options, key=f"{key_prefix}_status")

    filtered = df
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]
    if search:
        mask = filtered.apply(lambda row: search.lower() in " ".join(str(v) for v in row.values).lower(), axis=1)
        filtered = filtered[mask]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
