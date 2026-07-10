"""Thin wrapper around the Anthropic API that forces every agent call to
return validated, structured JSON instead of free text.

Every agent defines a Pydantic output model. We turn that model's JSON
schema into a single Anthropic "tool", force the model to call it
(tool_choice), and validate the tool call's input against the same model.
This is what makes agent output machine-readable and safe for downstream
agents to consume without a fragile "parse the markdown" step.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel

from career_copilot.core.pricing import estimate_cost

DEFAULT_MODEL = "claude-sonnet-5"

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


@dataclass
class UsageRecord:
    called_at: str
    model: str
    method: str  # "run_structured" or "run_with_web_search"
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    estimated_cost_usd: Optional[float]


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 8192):
        self.model = model
        self.max_tokens = max_tokens
        self.usage_log: List[UsageRecord] = []
        self._client = None  # lazily constructed so importing this module never requires a key

    def _record_usage(self, *, method: str, usage) -> None:
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        self.usage_log.append(UsageRecord(
            called_at=datetime.now(timezone.utc).isoformat(),
            model=self.model,
            method=method,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            estimated_cost_usd=estimate_cost(self.model, input_tokens, output_tokens),
        ))

    def total_cost_usd(self) -> Optional[float]:
        """Sum of every recorded call's estimated_cost_usd, or None if the model
        isn't in the pricing table (rather than silently reporting 0)."""
        costs = [r.estimated_cost_usd for r in self.usage_log]
        if any(c is None for c in costs):
            return None
        return sum(costs)

    def total_tokens(self) -> "dict[str, int]":
        return {
            "input_tokens": sum(r.input_tokens for r in self.usage_log),
            "output_tokens": sum(r.output_tokens for r in self.usage_log),
            "cache_creation_input_tokens": sum(r.cache_creation_input_tokens for r in self.usage_log),
            "cache_read_input_tokens": sum(r.cache_read_input_tokens for r in self.usage_log),
        }

    def _get_client(self):
        if self._client is not None:
            return self._client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Export it to run agents live, e.g.\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n"
                "Until then, use the *_sample_output.json fixtures in outputs/ to review agent behavior."
            )
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is not installed. Run: pip install -r requirements.txt"
            ) from exc
        self._client = Anthropic(api_key=api_key)
        return self._client

    def run_structured(self, *, system: str, user: str, output_model: Type[T]) -> T:
        """Call the model and force it to respond via a tool call matching output_model."""
        client = self._get_client()
        schema = output_model.model_json_schema()
        # Anthropic's tool input_schema doesn't need $defs stripped; pydantic v2 already
        # produces valid JSON Schema draft 2020-12, which the API accepts.
        tool_name = "emit_result"

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Emit the structured {output_model.__name__} result. This is the only allowed response.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )

        self._record_usage(method="run_structured", usage=response.usage)

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return output_model.model_validate(block.input)

        raise LLMError(f"Model response did not include the expected '{tool_name}' tool call.")

    def run_with_web_search(self, *, system: str, user: str, max_uses: int = 8) -> str:
        """Call the model with Anthropic's server-side web_search tool enabled and
        return its final text answer.

        Used by agents that need to ground claims about the real world (e.g. Company
        Intelligence) in current, citable sources instead of parametric knowledge —
        the model decides when and what to search; the search itself runs server-side
        within this single call. The returned text is meant to be fed into
        run_structured() as a second pass to shape it into a schema, keeping "did we
        research this" and "did we format this correctly" as separate concerns.
        """
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}],
        )
        self._record_usage(method="run_with_web_search", usage=response.usage)
        return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
