"""Create a provider by name. Add new presets here."""

from __future__ import annotations

from ..config import Settings
from .base import LLMProvider
from .groq import make_groq_provider
from .ollama import make_ollama_provider

PROVIDER_NAMES = ("groq", "ollama")


def get_provider(settings: Settings, name: str | None = None, model: str | None = None,
                 check: bool = True) -> LLMProvider:
    name = (name or settings.llm_provider).lower()
    if name == "groq":
        return make_groq_provider(settings, model)
    if name == "ollama":
        return make_ollama_provider(settings, model, check=check)
    raise ValueError(f"Unknown LLM provider {name!r}. Choose from: {', '.join(PROVIDER_NAMES)}")
