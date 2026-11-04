"""Groq chat completions through its OpenAI-compatible endpoint.

We call the official `openai` client directly instead of LangChain: it is the same
HTTP API, but gives us explicit timeouts, retries and access to `response_format`
with fewer dependencies.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import openai
from openai import OpenAI

from ..config import Settings


class LLMError(RuntimeError):
    """A provider call failed in a way the caller should record, not crash on."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_seconds: float


class GroqProvider:
    name = "groq"
    is_external = True   # data leaves the researcher's machine

    def __init__(self, api_key: str, model: str, base_url: str, temperature: float = 0.0,
                 timeout: float = 60.0, max_retries: int = 2, client: OpenAI | None = None):
        if not api_key:
            raise LLMError("GROQ_API_KEY is not set. Add it to your .env file.")
        self.model = model
        self.temperature = temperature
        self._client = client or OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "GroqProvider":
        return cls(
            api_key=settings.groq_api_key or "",
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    def generate(self, system: str, user: str, json_schema: dict | None = None) -> LLMResponse:
        """Return the model's text. Stage 2 always uses JSON-object mode; schema use comes in Stage 6."""
        started = time.monotonic()
        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_object"},
            )
        except openai.APIError as exc:
            raise LLMError(f"Groq request failed: {type(exc).__name__}: {exc}") from exc
        text = completion.choices[0].message.content or ""
        return LLMResponse(text=text, provider=self.name, model=self.model,
                           latency_seconds=round(time.monotonic() - started, 3))
