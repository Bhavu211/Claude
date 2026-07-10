"""Base class every Career Copilot agent implements.

The contract is deliberately narrow: an agent takes a validated Pydantic
input, returns a validated Pydantic output, and never touches another
agent's concerns. Orchestration (ordering, parallelism, conflict
resolution) is the Planner/Supervisor Agents' job, not any individual
agent's.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from pydantic import BaseModel

from career_copilot.core.llm_client import LLMClient

TIn = TypeVar("TIn", bound=BaseModel)
TOut = TypeVar("TOut", bound=BaseModel)


class BaseAgent(ABC, Generic[TIn, TOut]):
    name: str
    system_prompt: str
    input_model: Type[TIn]
    output_model: Type[TOut]

    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()

    @abstractmethod
    def build_user_prompt(self, data: TIn) -> str:
        """Turn validated input into the user-turn prompt sent to the model."""
        raise NotImplementedError

    def run(self, data: TIn) -> TOut:
        validated_input = self.input_model.model_validate(
            data.model_dump() if isinstance(data, BaseModel) else data
        )
        user_prompt = self.build_user_prompt(validated_input)
        return self.client.run_structured(
            system=self.system_prompt,
            user=user_prompt,
            output_model=self.output_model,
        )
