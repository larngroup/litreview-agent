"""The provider interface. The research pipeline only ever sees this."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

STRUCTURED_MODES = ("json_schema", "json_object", "none")


class LLMError(RuntimeError):
    """A provider call failed. The message is meant to be shown to the user."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    mode: str                 # structured-output mode actually used for this call
    latency_seconds: float


class LLMProvider(Protocol):
    name: str
    model: str
    temperature: float
    structured_mode: str
    is_external: bool         # True when prompts leave the researcher's computer

    def generate(self, system: str, user: str, json_schema: dict | None = None) -> LLMResponse: ...
