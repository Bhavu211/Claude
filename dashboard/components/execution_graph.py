"""Renders the live execution DAG as a Plotly figure — computed fresh from
whatever agents are actually part of the current run and their real
dependency edges (dashboard/discovery.py + dashboard/graph_layout.py),
never a fixed predrawn diagram."""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go

from dashboard.discovery import AgentMeta
from dashboard.graph_layout import compute_layout

STATUS_COLORS = {
    "pending": "#9AA0A6",
    "running": "#2563EB",
    "completed": "#16A34A",
    "failed": "#DC2626",
    "skipped": "#D97706",
}
STATUS_LABELS = {
    "pending": "Waiting",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
    "skipped": "Skipped",
}


def build_execution_graph_figure(
    agents: List[AgentMeta], statuses: Dict[str, str], running_agent_id: str = None,
) -> go.Figure:
    agent_by_id = {a.id: a for a in agents}
    agent_ids = list(agent_by_id.keys())
    depends_on = {a.id: [d for d in a.depends_on if d in agent_by_id] for a in agents}
    positions = compute_layout(agent_ids, depends_on)

    edge_x, edge_y = [], []
    for aid, deps in depends_on.items():
        x1, y1 = positions[aid]
        for dep in deps:
            x0, y0 = positions[dep]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1.5, color="rgba(150,150,150,0.5)"),
        hoverinfo="none", showlegend=False,
    )

    node_x, node_y, node_text, node_color, node_line_width, node_hover = [], [], [], [], [], []
    for aid in agent_ids:
        x, y = positions[aid]
        node_x.append(x)
        node_y.append(y)
        status = statuses.get(aid, "pending")
        node_text.append(agent_by_id[aid].display_name.replace(" Agent", ""))
        node_color.append(STATUS_COLORS.get(status, STATUS_COLORS["pending"]))
        node_line_width.append(4 if aid == running_agent_id else 1)
        node_hover.append(f"{agent_by_id[aid].display_name}<br>Status: {STATUS_LABELS.get(status, status)}<br>{agent_by_id[aid].description}")

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=node_text,
        textposition="bottom center", hovertext=node_hover, hoverinfo="text",
        marker=dict(
            size=46, color=node_color, line=dict(width=node_line_width, color="white"),
        ),
        showlegend=False,
    )

    from collections import Counter
    max_column_size = max(Counter(x for x, _ in positions.values()).values(), default=1)

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=max(320, 90 * max_column_size),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
