"""Dynamic agent discovery.

No agent, workflow, or dependency edge in this module is hardcoded. It
imports every module under `career_copilot/agents/`, finds the `BaseAgent`
subclass each one defines, and reads its real metadata directly off the
class: `name`, `input_model`/`output_model` fields, and its docstring.

For the 15 specialist agents, `AGENT_REGISTRY` (career_copilot/core/registry.py)
already carries a hand-verified category/description/requires/depends_on —
that registry is itself data, not code, and stays the ground truth for those
fields rather than being re-derived. For agents outside the registry (the
orchestration layer: Planner, Critic, Supervisor), category/requires/depends_on
are derived structurally: `depends_on` is any other discovered agent whose id
appears as `<id>_output` among this agent's input fields — so adding a new
orchestration agent that consumes `some_new_agent_output` automatically wires
the edge, no code change here required. Add or remove an agent module under
career_copilot/agents/ and the next discovery pass reflects it.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Dict, List, Optional

from pydantic import BaseModel

import career_copilot.agents as agents_pkg
from career_copilot.core.base_agent import BaseAgent
from career_copilot.core.registry import AGENT_BY_ID


class FieldMeta(BaseModel):
    name: str
    type: str
    required: bool


class AgentMeta(BaseModel):
    id: str
    class_name: str
    display_name: str
    category: str
    description: str
    input_fields: List[FieldMeta]
    output_fields: List[FieldMeta]
    requires: List[str]
    depends_on: List[str]
    module: str


def _fmt_type(annotation) -> str:
    return str(annotation).replace("typing.", "").replace("career_copilot.agents.", "")


def _extract_fields(model: type[BaseModel]) -> List[FieldMeta]:
    return [
        FieldMeta(name=name, type=_fmt_type(info.annotation), required=info.is_required())
        for name, info in model.model_fields.items()
    ]


def _find_agent_class(module) -> Optional[type]:
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseAgent) and obj is not BaseAgent and obj.__module__ == module.__name__:
            return obj
    return None


def discover_agents() -> List[AgentMeta]:
    """Scan career_copilot/agents/*.py and return one AgentMeta per agent
    actually found there — never a hardcoded list."""
    raw: Dict[str, dict] = {}

    for module_info in pkgutil.iter_modules(agents_pkg.__path__):
        agent_id = module_info.name
        module = importlib.import_module(f"career_copilot.agents.{agent_id}")
        agent_cls = _find_agent_class(module)
        if agent_cls is None:
            continue
        raw[agent_id] = {
            "class": agent_cls,
            "input_fields": _extract_fields(agent_cls.input_model),
            "output_fields": _extract_fields(agent_cls.output_model),
        }

    all_ids = set(raw.keys())
    metas: List[AgentMeta] = []

    for agent_id, info in raw.items():
        agent_cls = info["class"]
        registry_entry = AGENT_BY_ID.get(agent_id)

        if registry_entry is not None:
            category = registry_entry.category.value
            description = registry_entry.description
            requires = list(registry_entry.requires)
            depends_on = list(registry_entry.depends_on)
        else:
            category = "orchestration"
            description = (agent_cls.__doc__ or "").strip().split("\n")[0] or agent_cls.name
            requires = [f.name for f in info["input_fields"] if f.required]
            depends_on = sorted(
                other_id
                for other_id in all_ids
                if other_id != agent_id
                and any(f.name == f"{other_id}_output" for f in info["input_fields"])
            )

        metas.append(AgentMeta(
            id=agent_id,
            class_name=agent_cls.__name__,
            display_name=agent_cls.name,
            category=category,
            description=description,
            input_fields=info["input_fields"],
            output_fields=info["output_fields"],
            requires=requires,
            depends_on=depends_on,
            module=f"career_copilot.agents.{agent_id}",
        ))

    metas.sort(key=lambda m: (m.category != "orchestration", m.id))
    return metas


def get_agent_class(agent_id: str):
    module = importlib.import_module(f"career_copilot.agents.{agent_id}")
    return _find_agent_class(module)
