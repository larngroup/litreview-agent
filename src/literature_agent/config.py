"""Settings loaded from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a number, got {raw!r}") from exc


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def _str(name: str, default: str | None = None) -> str | None:
    raw = os.environ.get(name, "").strip()
    return raw or default


@dataclass(frozen=True)
class Settings:
    openalex_api_key: str | None
    contact_email: str | None
    llm_provider: str                 # "groq" or "ollama"
    llm_structured_mode: str          # "auto", "json_schema", "json_object" or "none"
    groq_api_key: str | None
    groq_model: str
    groq_base_url: str
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    llm_temperature: float
    llm_timeout_seconds: float
    llm_max_retries: int
    http_timeout_seconds: float
    http_max_retries: int
    data_dir: Path
    db_path: Path


def load_settings(env_file: str | os.PathLike | None = ".env") -> Settings:
    """Read settings. Real environment variables win over values in the .env file."""
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=False)
    data_dir = Path(_str("LITAGENT_DATA_DIR", "data"))
    return Settings(
        openalex_api_key=_str("OPENALEX_API_KEY"),
        contact_email=_str("CONTACT_EMAIL"),
        llm_provider=_str("LLM_PROVIDER", "groq").lower(),
        llm_structured_mode=_str("LLM_STRUCTURED_MODE", "auto").lower(),
        groq_api_key=_str("GROQ_API_KEY"),
        groq_model=_str("GROQ_MODEL", "openai/gpt-oss-20b"),
        groq_base_url=_str("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        ollama_base_url=_str("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_model=_str("OLLAMA_MODEL", "llama3.1:8b"),
        ollama_timeout_seconds=_float("OLLAMA_TIMEOUT_SECONDS", 300.0),
        llm_temperature=_float("LLM_TEMPERATURE", 0.0),
        llm_timeout_seconds=_float("LLM_TIMEOUT_SECONDS", 60.0),
        llm_max_retries=_int("LLM_MAX_RETRIES", 2),
        http_timeout_seconds=_float("HTTP_TIMEOUT_SECONDS", 30.0),
        http_max_retries=_int("HTTP_MAX_RETRIES", 4),
        data_dir=data_dir,
        db_path=Path(_str("LITAGENT_DB_PATH", str(data_dir / "literature.db"))),
    )
