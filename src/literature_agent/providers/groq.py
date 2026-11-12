"""Groq preset (hosted). Prompts and abstracts are sent to Groq's servers."""

from __future__ import annotations

from ..config import Settings
from .base import LLMError
from .openai_compatible import OpenAICompatibleProvider

# Models that Groq documents as supporting strict (constrained) JSON-schema output.
GROQ_STRICT_SCHEMA_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}


def make_groq_provider(settings: Settings, model: str | None = None) -> OpenAICompatibleProvider:
    if not settings.groq_api_key:
        raise LLMError("GROQ_API_KEY is not set. Add it to your .env file, or use LLM_PROVIDER=ollama.")
    model = model or settings.groq_model
    strict = model in GROQ_STRICT_SCHEMA_MODELS
    mode = settings.llm_structured_mode
    if mode == "auto":
        mode = "json_schema" if strict else "json_object"
    return OpenAICompatibleProvider(
        name="groq", base_url=settings.groq_base_url, api_key=settings.groq_api_key, model=model,
        temperature=settings.llm_temperature, timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries, structured_mode=mode, strict_schema=strict,
        is_external=True,
    )
