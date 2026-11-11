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
