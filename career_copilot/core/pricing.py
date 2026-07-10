"""Per-model token pricing, used to turn raw usage into an estimated cost.

Prices are USD per million tokens, standard (non-introductory) list pricing
as published by Anthropic. Anthropic's `web_search` server tool bills a
separate per-query fee on top of token usage that isn't reflected here —
this module only prices tokens, so `estimate_cost` on a research-grounded
agent's usage undercounts the true cost of that call.
"""

from __future__ import annotations

from typing import NamedTuple, Optional


class ModelPricing(NamedTuple):
    input_per_million: float
    output_per_million: float


PRICING = {
    "claude-fable-5": ModelPricing(10.00, 50.00),
    "claude-mythos-5": ModelPricing(10.00, 50.00),
    "claude-opus-4-8": ModelPricing(5.00, 25.00),
    "claude-opus-4-7": ModelPricing(5.00, 25.00),
    "claude-opus-4-6": ModelPricing(5.00, 25.00),
    "claude-sonnet-5": ModelPricing(3.00, 15.00),
    "claude-sonnet-4-6": ModelPricing(3.00, 15.00),
    "claude-haiku-4-5": ModelPricing(1.00, 5.00),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Returns None for an unrecognized model rather than guessing a price."""
    pricing = PRICING.get(model)
    if pricing is None:
        return None
    return (input_tokens / 1_000_000) * pricing.input_per_million + (
        output_tokens / 1_000_000
    ) * pricing.output_per_million
