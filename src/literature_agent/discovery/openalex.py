"""OpenAlex search over plain HTTP.

Why we no longer use pyalex here (it is still used in the Stage 1 notebook):
* pyalex 0.21 sets no request timeout, so a stalled connection can block forever;
* we need the same retry/pacing behaviour for every source;
* we can test it offline with an injected httpx client.
`reconstruct_abstract` and `work_to_paper` are unchanged from Stage 2.
"""

from __future__ import annotations

import logging

from ..models import Paper, utc_now
from .http import PoliteClient

log = logging.getLogger(__name__)

OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_FIELDS = [
    "id", "doi", "title", "publication_year", "authorships",
    "abstract_inverted_index", "keywords",
]
MAX_RECORDS = 10_000


def reconstruct_abstract(inverted_index: object) -> str:
    """Rebuild an abstract from OpenAlex's inverted index {"word": [positions]}."""
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""
    words_by_position: dict[int, str] = {}
    for word, positions in inverted_index.items():
        if not isinstance(word, str) or not isinstance(positions, (list, tuple)):
            continue
        for position in positions:
            if isinstance(position, int) and not isinstance(position, bool) and position >= 0:
                words_by_position[position] = word
    return " ".join(words_by_position[p] for p in sorted(words_by_position)).strip()


def work_to_paper(work: dict, query: str, retrieved_at=None) -> Paper:
    """Convert one OpenAlex work (a dict) into a validated Paper."""
    authors = []
    for authorship in work.get("authorships") or []:
        author = (authorship or {}).get("author") or {}
        if author.get("display_name"):
            authors.append(author["display_name"])
    keywords = [
        entry["display_name"]
        for entry in work.get("keywords") or []
        if isinstance(entry, dict) and entry.get("display_name")
    ]
    return Paper(
        source="openalex",
        source_id=work.get("id"),
        doi=work.get("doi"),
        title=work.get("title"),
        year=work.get("publication_year"),
        authors=authors,
        keywords=keywords,
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        query=query,
        retrieved_at=retrieved_at or utc_now(),
    )


def validate_search_args(query: str, limit: int) -> str:
    query = (query or "").strip()
    if not query:
        raise ValueError("The search query is empty.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RECORDS:
        raise ValueError(f"limit must be an integer between 1 and {MAX_RECORDS}, got {limit!r}")
    return query


class OpenAlexSource:
    name = "openalex"

    def __init__(self, http: PoliteClient, api_key: str | None = None):
        self.http = http
        self.api_key = api_key

    def search(self, query: str, limit: int = 100) -> list[Paper]:
        query = validate_search_args(query, limit)
        retrieved_at = utc_now()
        params = {"search": query, "per_page": min(limit, 200), "cursor": "*",
                  "select": ",".join(OPENALEX_FIELDS)}
        if self.api_key:
            params["api_key"] = self.api_key   # documented way to authenticate
        papers: list[Paper] = []
        seen: set[str] = set()
        while len(papers) < limit:
            data = self.http.get_json(OPENALEX_URL, params)
            results = data.get("results") or []
            for work in results:
                paper = work_to_paper(work, query, retrieved_at)
                key = paper.source_id or paper.doi
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                papers.append(paper)
                if len(papers) >= limit:
                    break
            next_cursor = (data.get("meta") or {}).get("next_cursor")
            log.info("OpenAlex: %d papers so far", len(papers))
            if not results or not next_cursor:
                break
            params["cursor"] = next_cursor
        return papers
