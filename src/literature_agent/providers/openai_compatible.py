"""One client for every OpenAI-compatible chat API (Groq, Ollama, LM Studio, vLLM, ...).

Structured output support differs between providers and models, so we try the
strongest mode first and fall back:

    json_schema (constrained to our schema)  ->  json_object (any valid JSON)  ->  none (plain text)

Whatever mode is used, the caller still validates the JSON with Pydantic.
"""

from __future__ import annotations

import logging
import time

import openai
from openai import OpenAI

from .base import STRUCTURED_MODES, LLMError, LLMResponse

log = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    def __init__(self, *, name: str, base_url: str, api_key: str, model: str,
                 temperature: float = 0.0, timeout: float = 60.0, max_retries: int = 2,
                 structured_mode: str = "json_schema", strict_schema: bool = False,
                 is_external: bool = True):
        if structured_mode not in STRUCTURED_MODES:
            raise ValueError(f"structured_mode must be one of {STRUCTURED_MODES}, got {structured_mode!r}")
        if not model:
            raise LLMError(f"No model configured for provider {name!r}.")
        self.name = name
        self.model = model
        self.temperature = temperature
        self.structured_mode = structured_mode
        self.strict_schema = strict_schema
        self.is_external = is_external
        self.base_url = base_url
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)

    def _response_format(self, mode: str, json_schema: dict | None) -> dict | None:
        if mode == "json_schema" and json_schema is not None:
            return {"type": "json_schema",
                    "json_schema": {"name": "output", "strict": self.strict_schema, "schema": json_schema}}
        if mode in ("json_schema", "json_object"):
            return {"type": "json_object"}
        return None

    def _modes_to_try(self, json_schema: dict | None) -> list[str]:
        order = list(STRUCTURED_MODES[STRUCTURED_MODES.index(self.structured_mode):])
        if json_schema is None and "json_schema" in order:
            order.remove("json_schema")
        return order or ["none"]

    def generate(self, system: str, user: str, json_schema: dict | None = None) -> LLMResponse:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        started = time.monotonic()
        last_error: Exception | None = None
        for mode in self._modes_to_try(json_schema):
            kwargs = {"model": self.model, "temperature": self.temperature, "messages": messages}
            response_format = self._response_format(mode, json_schema)
            if response_format:
                kwargs["response_format"] = response_format
            try:
                completion = self._client.chat.completions.create(**kwargs)
            except openai.BadRequestError as exc:
                # 400: this model/provider rejected the mode (or failed to satisfy the
                # schema). Try the next, weaker mode instead of failing the paper.
                log.warning("%s rejected mode %s: %s; falling back", self.name, mode, exc)
                last_error = exc
                continue
            except openai.AuthenticationError as exc:
                raise LLMError(f"{self.name}: authentication failed - check your API key.") from exc
            except openai.NotFoundError as exc:
                raise LLMError(f"{self.name}: model {self.model!r} not found ({exc}).") from exc
            except openai.APITimeoutError as exc:
                raise LLMError(f"{self.name}: request timed out.") from exc
            except openai.APIConnectionError as exc:
                raise LLMError(f"{self.name}: cannot connect to {self.base_url} ({exc}).") from exc
            except openai.APIError as exc:   # rate limits after retries, 5xx, ...
                raise LLMError(f"{self.name}: {type(exc).__name__}: {exc}") from exc
            choice = completion.choices[0] if completion.choices else None
            text = (choice.message.content if choice and choice.message else None) or ""
            return LLMResponse(text=text, provider=self.name, model=self.model, mode=mode,
                               latency_seconds=round(time.monotonic() - started, 3))
        raise LLMError(f"{self.name}: every structured-output mode was rejected; last error: {last_error}")
