"""Layered (topological) layout for the execution graph — computed fresh
from whatever subset of agents is actually part of the current run, not a
fixed diagram. An agent with no in-set dependencies sits at layer 0; every
other agent sits one layer past the deepest of its own dependencies."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple


def compute_layout(agent_ids: List[str], depends_on: Dict[str, List[str]]) -> Dict[str, Tuple[int, float]]:
    agent_set = set(agent_ids)
    layer: Dict[str, int] = {}

    def get_layer(aid: str, _stack: frozenset = frozenset()) -> int:
        if aid in layer:
            return layer[aid]
        if aid in _stack:
            raise ValueError(f"Dependency cycle detected at {aid!r}")
        deps = [d for d in depends_on.get(aid, []) if d in agent_set]
        layer[aid] = 0 if not deps else 1 + max(get_layer(d, _stack | {aid}) for d in deps)
        return layer[aid]

    for aid in agent_ids:
        get_layer(aid)

    by_layer: Dict[int, List[str]] = defaultdict(list)
    for aid in agent_ids:
        by_layer[layer[aid]].append(aid)

    positions: Dict[str, Tuple[int, float]] = {}
    for l, ids in by_layer.items():
        ids.sort()
        n = len(ids)
        for i, aid in enumerate(ids):
            positions[aid] = (l, i - (n - 1) / 2)
    return positions
