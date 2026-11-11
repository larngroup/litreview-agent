"""Crossref REST API search (https://api.crossref.org).

Etiquette: send a contact address (`mailto`) to use the "polite pool", keep the
request rate low, and back off on HTTP 429. Crossref metadata is supplied by
publishers, so abstracts are often missing and keywords ("subject") are rare.
"""

from __future__ import annotations

import html
import logging
import re

from ..models import Paper, utc_now
from .http import PoliteClient
from .openalex import validate_search_args

log = logging.getLogger(__name__)

CROSSREF_URL = "https://api.crossref.org/works"
CROSSREF_FIELDS = ["DOI", "title", "author", "issued", "published", "abstract", "subject", "type"]
_TAG = re.compile(r"<[^>]+>")


def clean_jats(text: object) -> str:
    """Crossref abstracts are JATS XML fragments: '<jats:p>Text</jats:p>' -> 'Text'."""
    if not isinstance(text, str):
        return ""
    without_tags = _TAG.sub(" ", text)
    cleaned = " ".join(html.unescape(without_tags).split())
    return re.sub(r"^(abstract)\s*[:.]?\s+", "", cleaned, flags=re.IGNORECASE)


def _year(item: dict) -> int | None:
    for field in ("issued", "published", "published-print", "published-online"):
        parts = (item.get(field) or {}).get("date-parts") or []
        if parts and parts[0] and isinstance(parts[0][0], int):
            return parts[0][0]
    return None


def item_to_paper(item: dict, query: str, retrieved_at=None) -> Paper:
    titles = item.get("title") or []
    title = titles[0] if isinstance(titles, list) and titles else None
    authors = []
    for author in item.get("author") or []:
        name = " ".join(p for p in (author.get("given"), author.get("family")) if p) or author.get("name")
        if name:
            authors.append(name)
    doi = item.get("DOI")
    return Paper(
        source="crossref",
        source_id=f"https://doi.org/{doi.lower()}" if isinstance(doi, str) else None,
        doi=doi,
        title=title,
        year=_year(item),
        authors=authors,
        keywords=[s for s in item.get("subject") or [] if isinstance(s, str)],
        abstract=clean_jats(item.get("abstract")),
        query=query,
        retrieved_at=retrieved_at or utc_now(),
    )


class CrossrefSource:
    name = "crossref"

    def __init__(self, http: PoliteClient, contact_email: str | None = None):
        self.http = http
        self.contact_email = contact_email

    def search(self, query: str, limit: int = 100) -> list[Paper]:
        query = validate_search_args(query, limit)
        retrieved_at = utc_now()
        params = {"query": query, "rows": min(limit, 100), "cursor": "*",
          "sort": "score", "order": "desc",
          "select": ",".join(CROSSREF_FIELDS)}
        if self.contact_email:
            params["mailto"] = self.contact_email
        papers: list[Paper] = []
        seen: set[str] = set()
        while len(papers) < limit:
            message = self.http.get_json(CROSSREF_URL, params).get("message") or {}
            items = message.get("items") or []
            for item in items:
                paper = item_to_paper(item, query, retrieved_at)
                if paper.doi and paper.doi in seen:
                    continue
                if paper.doi:
                    seen.add(paper.doi)
                papers.append(paper)
                if len(papers) >= limit:
                    break
            log.info("Crossref: %d papers so far", len(papers))
            next_cursor = message.get("next-cursor")
            if not items or not next_cursor:
                break
            params["cursor"] = next_cursor
        return papers
