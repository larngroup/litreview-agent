"""Academic search sources and a registry to create them by name.

To add a source (e.g. Europe PMC): write a class with `name` and
`search(query, limit) -> list[Paper]`, then register it in `make_source`.
"""

from __future__ import annotations

from typing import Protocol

from ..config import Settings
from ..models import Paper
from .crossref import CrossrefSource
from .http import PoliteClient, SourceError
from .openalex import OpenAlexSource

SOURCE_NAMES = ("openalex", "crossref")


class SearchSource(Protocol):
    name: str

    def search(self, query: str, limit: int = 100) -> list[Paper]: ...


def make_source(name: str, settings: Settings, http: PoliteClient | None = None) -> SearchSource:
    common = dict(timeout=settings.http_timeout_seconds, max_retries=settings.http_max_retries,
                  contact_email=settings.contact_email)
    if name == "openalex":
        return OpenAlexSource(http or PoliteClient(min_interval_seconds=0.1, **common),
                              api_key=settings.openalex_api_key)
    if name == "crossref":
        # Crossref: ~1 request/s anonymously, more in the polite pool (with mailto).
        interval = 0.5 if settings.contact_email else 1.1
        return CrossrefSource(http or PoliteClient(min_interval_seconds=interval, **common),
                              contact_email=settings.contact_email)
    raise ValueError(f"Unknown source {name!r}. Choose from: {', '.join(SOURCE_NAMES)}")


__all__ = ["SOURCE_NAMES", "SearchSource", "SourceError", "make_source"]
