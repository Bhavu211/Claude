from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import db

st.set_page_config(page_title="Companies — Career Copilot", page_icon="🏢", layout="wide")
db.init_db()

st.title("🏢 Companies")

companies = db.list_companies()
if not companies:
    st.info("No companies researched yet — run an analysis with a company name from **New Analysis**.")
    st.stop()

for company in companies:
    app_count = db.get_company_application_count(company["name"])
    with st.expander(f"**{company['name']}** — {app_count} application(s)", expanded=False):
        st.write(f"**Industry:** {company['industry'] or '—'}")
        st.write(f"**Culture:** {company['culture'] or '—'}")
        for label, field in [("Products", "products"), ("Tech stack", "tech_stack"), ("Recent news", "recent_news"), ("Required skills", "required_skills")]:
            raw = company.get(field)
            if raw:
                items = json.loads(raw)
                st.write(f"**{label}:**")
                st.write(", ".join(items) if items else "—")
        st.caption(f"Last researched: {company['last_researched_at'] or 'never'}")

        apps = db.list_applications(company_name=company["name"])
        if apps:
            st.write("**Previous applications to this company:**")
            for a in apps:
                st.write(f"- #{a['id']} — {a['job_title']} ({a['created_at'][:10]}) — ATS {a['ats_score'] or '—'}")
