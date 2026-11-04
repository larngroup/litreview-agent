"""Validated data models shared by every part of the application."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

_DOI_PREFIXES = (
    "https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def normalise_doi(doi: object) -> str | None:
    """Return a bare, lower-case DOI ('10.x/y') or None if `doi` is not a DOI."""
    if not isinstance(doi, str):
        return None
    value = doi.strip().lower()
    for prefix in _DOI_PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix):]
    value = value.strip()
    return value if value.startswith("10.") and "/" in value else None


class Paper(BaseModel):
    """One bibliographic record as returned by ONE source at ONE moment."""

    model_config = ConfigDict(extra="ignore")

    source: str                         # e.g. "openalex"
    source_id: str | None = None        # e.g. "https://openalex.org/W123"
    doi: str | None = None
    title: str | None = None
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    abstract: str = ""
    query: str = ""
    retrieved_at: datetime = Field(default_factory=utc_now)

    @field_validator("doi", mode="before")
    @classmethod
    def _clean_doi(cls, value: object) -> str | None:
        return normalise_doi(value)

    @field_validator("title", mode="before")
    @classmethod
    def _clean_title(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        value = " ".join(value.split())
        return value or None

    @field_validator("abstract", mode="before")
    @classmethod
    def _clean_abstract(cls, value: object) -> str:
        return " ".join(value.split()) if isinstance(value, str) else ""

    @field_validator("year", mode="before")
    @classmethod
    def _clean_year(cls, value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and 1000 <= value <= 2100:
            return value
        return None

    @computed_field  # included in model_dump(), so JSON files keep the field
    @property
    def has_abstract(self) -> bool:
        return bool(self.abstract)

    @property
    def display_title(self) -> str:
        return self.title or "(no title)"
