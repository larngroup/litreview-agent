"""Ollama preset (local inference through Ollama's OpenAI-compatible /v1 API)."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from ..config import Settings
from .base import LLMError
from .openai_compatible import OpenAICompatibleProvider

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _root_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    return root[:-3] if root.endswith("/v1") else root


def is_local(base_url: str) -> bool:
    return (urlparse(base_url).hostname or "") in LOCAL_HOSTS


def list_ollama_models(base_url: str, timeout: float = 5.0) -> list[str]:
    """Names of the models installed in Ollama (GET /api/tags)."""
    url = _root_url(base_url) + "/api/tags"
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise LLMError(f"Cannot reach Ollama at {url}. Is it running? Start it with `ollama serve`. ({exc})") from exc
    return [m.get("name", "") for m in response.json().get("models", [])]


def make_ollama_provider(settings: Settings, model: str | None = None,
                         check: bool = True) -> OpenAICompatibleProvider:
    model = model or settings.ollama_model
    if check:
        installed = list_ollama_models(settings.ollama_base_url)
        # "llama3.1" and "llama3.1:latest" refer to the same model in Ollama.
        names = set(installed) | {n.removesuffix(":latest") for n in installed}
        if model not in names:
            raise LLMError(f"Ollama model {model!r} is not installed. Run `ollama pull {model}`. "
                           f"Installed: {', '.join(installed) or 'none'}")
    mode = "json_schema" if settings.llm_structured_mode == "auto" else settings.llm_structured_mode
    return OpenAICompatibleProvider(
        name="ollama", base_url=settings.ollama_base_url, api_key="ollama",  # Ollama ignores the key
        model=model, temperature=settings.llm_temperature, timeout=settings.ollama_timeout_seconds,
        max_retries=settings.llm_max_retries, structured_mode=mode, strict_schema=False,
        # A remote Ollama server is still an external service for privacy purposes.
        is_external=not is_local(settings.ollama_base_url),
    )
