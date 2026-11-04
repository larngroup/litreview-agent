"""OpenAlex search, moved from the notebook (logic unchanged since Stage 1)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

import pyalex
from pyalex import Works

from ..models import Paper, utc_now

log = logging.getLogger(__name__)

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


def configure_pyalex(api_key: str | None, contact_email: str | None, max_retries: int = 3) -> None:
    pyalex.config.api_key = api_key
    pyalex.config.email = contact_email
    pyalex.config.max_retries = max_retries
    pyalex.config.retry_backoff_factor = 0.5
    pyalex.config.retry_http_codes = [429, 500, 502, 503, 504]


def _default_pager(query: str, per_page: int, n_max: int) -> Iterable[Iterable[dict]]:
    return Works().search(query).select(OPENALEX_FIELDS).paginate(per_page=per_page, n_max=n_max)


def search_openalex(
    query: str,
    limit: int = 100,
    pager_factory: Callable[[str, int, int], Iterable[Iterable[dict]]] = _default_pager,
) -> list[Paper]:
    """Return at most `limit` unique papers for `query`.

    `pager_factory` exists so tests can replace the network call with fake pages.
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("The search query is empty.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RECORDS:
        raise ValueError(f"limit must be an integer between 1 and {MAX_RECORDS}, got {limit!r}")

    retrieved_at = utc_now()
    papers: list[Paper] = []
    seen: set[str] = set()
    for page_number, page in enumerate(pager_factory(query, min(limit, 200), limit), start=1):
        for work in page:
            paper = work_to_paper(work, query, retrieved_at)
            key = paper.source_id or paper.doi
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            papers.append(paper)
            if len(papers) >= limit:
                break
        log.info("OpenAlex page %d: %d papers so far", page_number, len(papers))
        if len(papers) >= limit:
            break
    return papers
