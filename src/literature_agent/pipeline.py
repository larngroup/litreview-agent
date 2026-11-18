"""Workflows that combine discovery, storage and screening.

The CLI and (from Stage 7) the web interface both call these functions, so the
research logic lives in exactly one place.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from .screening.relevance import PROMPT_VERSION, Criteria, ScreeningResult, screen_paper
from .storage import database as db


def run_search(conn, project_id: int, query: str, limit: int, source) -> dict:
    """Run ONE source, store records with provenance, and log the run.
    PRESERVA O KeyboardInterrupt do stage 3: se o utilizador carregar em Ctrl+C, a pesquisa é interrompida e o estado é guardado.
    A função run_multi_search() já captura erros normais individualmente, 
    mas não captura KeyboardInterrupt. Isso é desejável: se carregares em Ctrl+C durante a pesquisa OpenAlex,
    o programa interrompe a operação, em vez de avançar automaticamente para o Crossref.

    Como o novo HTTP obtém primeiro os resultados da API e só depois os guarda,
    uma interrupção durante a chamada HTTP pode não preservar os artigos dessa chamada.
    Mas agora a run fica corretamente marcada como interrupted."""


    run_id = db.start_search_run(conn, project_id, source.name, query, limit)
    db.log_event(
        conn, project_id, "info", "search_started",
        f"{source.name} search: {query!r}",
        {"run_id": run_id, "limit": limit},
    )

    new = duplicates = 0
    matched = Counter()
    papers = []

    try:
        papers = source.search(query, limit=limit)

        for paper in papers:
            result = db.add_paper(conn, project_id, run_id, paper)
            new += result.new_in_project
            duplicates += not result.new_in_project

            if result.matched_by:
                matched[result.matched_by] += 1

        db.finish_search_run(
            conn, run_id, status="completed",
            n_retrieved=len(papers),
            n_new=new,
            n_duplicates=duplicates,
        )

    except KeyboardInterrupt:
        db.finish_search_run(
            conn, run_id,
            status="interrupted",
            n_retrieved=new + duplicates,
            n_new=new,
            n_duplicates=duplicates,
            error="Search interrupted by user (Ctrl+C)",
        )
        db.log_event(
            conn, project_id, "warning", "search_interrupted",
            f"{source.name} search interrupted by user",
            {"run_id": run_id, "source": source.name},
        )
        raise

    except Exception as exc:
        db.finish_search_run(
            conn, run_id,
            status="failed",
            n_retrieved=new + duplicates,
            n_new=new,
            n_duplicates=duplicates,
            error=f"{type(exc).__name__}: {exc}",
        )
        db.log_event(
            conn, project_id, "error", "search_failed",
            str(exc),
            {"run_id": run_id, "source": source.name},
        )
        raise

    summary = {
        "run_id": run_id,
        "source": source.name,
        "retrieved": len(papers),
        "new": new,
        "duplicates": duplicates,
        "matched_by": dict(matched),
        "without_abstract": sum(not p.has_abstract for p in papers),
    }

    db.log_event(
        conn, project_id, "info", "search_completed",
        f"{source.name} search finished", summary,
    )
    return summary



def run_multi_search(conn, project_id: int, query: str, limit: int, sources) -> list[dict]:
    """Run several sources. A failing source is recorded and does not stop the others."""
    summaries = []
    for source in sources:
        try:
            summaries.append(run_search(conn, project_id, query, limit, source))
        except Exception as exc:
            summaries.append({"source": source.name, "error": f"{type(exc).__name__}: {exc}"})
    return summaries


def run_screening(conn, project_id: int, provider, *, retry_failed: bool = False,
                  redo_all: bool = False, max_papers: int | None = None,
                  on_progress: Callable[[int, int, ScreeningResult], None] | None = None) -> Counter:
    """Screen the project's papers against its CURRENT criteria.

    Papers already screened with the same criteria and prompt version are skipped,
    so an interrupted run can simply be started again.
    """
    project = db.require_project(conn, project_id)
    criteria = Criteria.from_project(project)
    criteria_hash = criteria.fingerprint()
    latest = db.latest_screenings(conn, project_id, criteria_hash)
    todo = [p for p in db.project_papers(conn, project_id)
            if redo_all or p["id"] not in latest
            or (retry_failed and latest[p["id"]]["status"] == "failed")]
    if max_papers is not None:
        todo = todo[:max_papers]
    run_settings = {"temperature": getattr(provider, "temperature", None),
                    "structured_mode": getattr(provider, "structured_mode", "json_object"),
                    "external": provider.is_external, "criteria": criteria.model_dump()}
    db.log_event(conn, project_id, "info", "screening_started", f"Screening {len(todo)} papers",
                 {"provider": provider.name, "model": provider.model, "prompt_version": PROMPT_VERSION,
                  "criteria_hash": criteria_hash, **run_settings})
    counts: Counter = Counter()
    for index, row in enumerate(todo, start=1):
        result = screen_paper(db.paper_from_row(row), criteria, provider)
        db.add_screening(
            conn, project_id=project_id, paper_id=row["id"], status=result.status,
            decision=result.decision, reason=result.reason, details=result.details,
            provider=result.provider, model=result.model, prompt_version=PROMPT_VERSION,
            criteria_hash=criteria_hash, settings=run_settings,
            raw_response=result.raw_response, error=result.error,
        )
        if result.status == "failed":
            db.log_event(conn, project_id, "warning", "screening_failed", result.error or "unknown error",
                         {"paper_id": row["id"]})
        counts[result.status] += 1
        if on_progress:
            on_progress(index, len(todo), result)
    db.log_event(conn, project_id, "info", "screening_completed", "Screening finished", dict(counts))
    return counts


# --------------------------------------------------------------------------- Stage 8: full text

FULLTEXT_SUBSETS = ("human_include", "include_any", "all")


def fulltext_candidates(conn, project_id: int, subset: str = "human_include") -> list[dict]:
    """human_include: a human said include; include_any: human include OR model include not yet
    reviewed (useful before full review); all: every paper in the project."""
    papers = db.project_papers(conn, project_id, Criteria.from_project(db.require_project(conn, project_id)).fingerprint())
    if subset == "human_include":
        return [p for p in papers if p["final_decision"] == "include"]
    if subset == "include_any":
        return [p for p in papers if p["final_decision"] == "include"
                or (p["final_decision"] is None and (p["screening"] or {}).get("decision") == "include")]
    if subset == "all":
        return papers
    raise ValueError(f"subset must be one of {FULLTEXT_SUBSETS}")


def _openalex_id(conn, paper_id: int) -> str | None:
    row = conn.execute("SELECT source_id FROM paper_sources WHERE paper_id = ? AND source = 'openalex' "
                       "AND source_id IS NOT NULL LIMIT 1", (paper_id,)).fetchone()
    return row["source_id"] if row else None


def process_fulltext(conn, project_id: int, paper: dict, *, http, data_dir, openalex_api_key=None,
                     contact_email=None, retry_failed: bool = False, download_client=None) -> str:
    """Locate -> download -> parse one paper. Returns its final state. Never deletes the paper."""
    from pathlib import Path

    from .discovery.http import SourceError
    from .fulltext import store
    from .fulltext.download import DownloadError, download_pdf
    from .fulltext.locate import locate_open_access
    from .fulltext.pdf_text import ParseError, extract_pages

    pid = paper["id"]
    asset = store.get_asset(conn, pid)
    if asset and asset["parse_status"] == "parsed":
        return "parsed"

    # 1. Locate a legal open-access copy.
    needs_lookup = asset is None or asset["access_status"] == "lookup_failed" or (
        retry_failed and asset["access_status"] == "not_found")
    if needs_lookup:
        openalex_id = _openalex_id(conn, pid)
        if not paper["doi"] and not openalex_id:
            store.save_asset(conn, pid, access_status="no_identifier", download_status="not_applicable",
                             parse_status="not_applicable", error="No DOI or OpenAlex id to look up.")
            return "no_identifier"
        try:
            location = locate_open_access(http, doi=paper["doi"], openalex_id=openalex_id,
                                          openalex_api_key=openalex_api_key, contact_email=contact_email)
        except SourceError as exc:
            store.save_asset(conn, pid, access_status="lookup_failed", error=str(exc))
            return "lookup_failed"
        if location is None:
            store.save_asset(conn, pid, access_status="not_found", download_status="not_applicable",
                             parse_status="not_applicable", error=None)
            return "not_found"
        store.save_asset(conn, pid, access_status="open_access", locator=location.locator,
                         pdf_url=location.pdf_url, landing_url=location.landing_url, license=location.license,
                         oa_version=location.version, download_status="pending", parse_status="pending", error=None)
        asset = store.get_asset(conn, pid)
    if asset["access_status"] != "open_access":
        return asset["access_status"]

    # 2. Download the PDF (only from the open-access URL that was reported).
    if asset["download_status"] == "pending" or (retry_failed and asset["download_status"] == "failed"):
        if not asset["pdf_url"]:
            store.save_asset(conn, pid, download_status="failed",
                             error=f"No direct PDF link. Open the landing page manually: {asset['landing_url']}")
            return "download_failed"
        try:
            downloaded = download_pdf(asset["pdf_url"], Path(data_dir) / "fulltext" / f"{pid}.pdf",
                                      client=download_client, contact_email=contact_email)
        except DownloadError as exc:
            store.save_asset(conn, pid, download_status="failed", error=str(exc))
            return "download_failed"
        store.save_asset(conn, pid, download_status="downloaded", file_path=str(downloaded.path),
                         sha256=downloaded.sha256, size_bytes=downloaded.size_bytes, error=None)
        asset = store.get_asset(conn, pid)
    if asset["download_status"] != "downloaded":
        return "download_failed"

    # 3. Extract text page by page.
    if asset["parse_status"] == "pending" or (retry_failed and asset["parse_status"] == "failed"):
        try:
            pages = extract_pages(Path(asset["file_path"]))
        except ParseError as exc:
            store.save_asset(conn, pid, parse_status="failed", error=str(exc))
            return "parse_failed"
        store.save_pages(conn, asset["id"], pages)
        store.save_asset(conn, pid, parse_status="parsed", n_pages=len(pages), error=None)
        return "parsed"
    return "parse_failed"


def run_fulltext(conn, project_id: int, *, http, data_dir, openalex_api_key=None, contact_email=None,
                 subset: str = "human_include", retry_failed: bool = False, download_client=None,
                 on_progress: Callable[[int, int, str], None] | None = None) -> Counter:
    papers = fulltext_candidates(conn, project_id, subset)
    db.log_event(conn, project_id, "info", "fulltext_started", f"Full-text retrieval for {len(papers)} papers",
                 {"subset": subset})
    counts: Counter = Counter()
    for index, paper in enumerate(papers, start=1):
        state = process_fulltext(conn, project_id, paper, http=http, data_dir=data_dir,
                                 openalex_api_key=openalex_api_key, contact_email=contact_email,
                                 retry_failed=retry_failed, download_client=download_client)
        counts[state] += 1
        if state in ("lookup_failed", "download_failed", "parse_failed"):
            db.log_event(conn, project_id, "warning", f"fulltext_{state}", f"Paper {paper['id']}: {state}",
                         {"paper_id": paper["id"]})
        if on_progress:
            on_progress(index, len(papers), state)
    db.log_event(conn, project_id, "info", "fulltext_completed", "Full-text retrieval finished", dict(counts))
    return counts
