from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import db

st.set_page_config(page_title="Outputs — Career Copilot", page_icon="📦", layout="wide")
db.init_db()

st.title("📦 Outputs")

apps = [a for a in db.list_applications() if a["output_folder"]]
if not apps:
    st.info("No completed applications with saved outputs yet.")
    st.stop()

labels = [f"#{a['id']} — {a['company_name']} / {a['job_title']} ({a['created_at'][:10]})" for a in apps]
selected = st.selectbox("Select an application", labels)
app = apps[labels.index(selected)]

folder = Path(app["output_folder"])
if not folder.exists():
    st.error(f"Output folder no longer exists: `{folder}`")
    st.stop()

st.caption(f"Folder: `{folder}`")

files = sorted(folder.iterdir())
for f in files:
    if not f.is_file():
        continue
    col1, col2 = st.columns([4, 1])
    with col1:
        with st.expander(f.name):
            if f.suffix in (".md", ".txt", ".json"):
                content = f.read_text(encoding="utf-8", errors="replace")
                st.code(content[:5000] + ("\n... (truncated)" if len(content) > 5000 else ""), language="markdown" if f.suffix == ".md" else ("json" if f.suffix == ".json" else None))
            else:
                st.caption("Preview not available for this file type.")
    with col2:
        st.download_button("Download", data=f.read_bytes(), file_name=f.name, key=f"dl_{f.name}")
