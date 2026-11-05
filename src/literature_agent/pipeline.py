"""Workflows that combine discovery, storage and screening.

The CLI and (from Stage 7) the web interface both call these functions, so the
research logic lives in exactly one place.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable

from .discovery.openalex import search_openalex
from .screening.relevance import PROMPT_VERSION, screen_paper
from .storage import database as db


def topic_criteria_hash(topic: str, prompt_version: str = PROMPT_VERSION) -> str:
    """Identifies 'which question was asked'. Different topic => different hash => re-screen."""
    payload = json.dumps({"topic": topic.strip(), "prompt_version": prompt_version}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# TEMPORARY RUN SEARCH THAT SIMULATES CTRL+C INTERRUPT, FOR TESTING PURPOSES
"""
def run_search(conn, project_id: int, query: str, limit: int,
               search_fn: Callable = search_openalex) -> dict:

    run_id = db.start_search_run(conn, project_id, "openalex", query, limit)

    print(f"[DEBUG] Run {run_id} criada com status='running'", flush=True)

    db.log_event(
        conn, project_id, "info", "search_started",
        f"OpenAlex search: {query!r}",
        {"run_id": run_id, "limit": limit},
    )

    try:
        print("[DEBUG] A entrar no bloco try", flush=True)

        # TESTE TEMPORÁRIO — simula Ctrl+C sem chamar a API
        print("[DEBUG] A simular KeyboardInterrupt!", flush=True)
        raise KeyboardInterrupt

        papers = search_fn(query, limit=limit)

    except Exception as exc:
        print("[DEBUG] Entrou no except Exception", flush=True)

        db.finish_search_run(
            conn, run_id, status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        print("[DEBUG] finish_search_run(status='failed') executado", flush=True)

        db.log_event(
            conn, project_id, "error", "search_failed",
            str(exc), {"run_id": run_id},
        )
        raise

    new = duplicates = 0
    for paper in papers:
        result = db.add_paper(conn, project_id, run_id, paper)
        new += result.new_in_project
        duplicates += not result.new_in_project

    print("[DEBUG] Antes de finish_search_run(status='completed')", flush=True)

    db.finish_search_run(
        conn, run_id, status="completed",
        n_retrieved=len(papers),
        n_new=new,
        n_duplicates=duplicates,
    )

    print("[DEBUG] finish_search_run(status='completed') executado", flush=True)

    summary = {
        "run_id": run_id,
        "retrieved": len(papers),
        "new": new,
        "duplicates": duplicates,
        "without_abstract": sum(not p.has_abstract for p in papers),
    }

    db.log_event(
        conn, project_id, "info", "search_completed",
        "OpenAlex search finished", summary,
    )
    return summary
"""

def run_search(conn, project_id: int, query: str, limit: int,
               search_fn: Callable = search_openalex) -> dict:
    run_id = db.start_search_run(conn, project_id, "openalex", query, limit)
    db.log_event(conn, project_id, "info", "search_started", f"OpenAlex search: {query!r}",
                 {"run_id": run_id, "limit": limit})
    try:
        papers = search_fn(query, limit=limit)
    except Exception as exc:
        db.finish_search_run(conn, run_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        db.log_event(conn, project_id, "error", "search_failed", str(exc), {"run_id": run_id})
        raise
    new = duplicates = 0
    for paper in papers:
        result = db.add_paper(conn, project_id, run_id, paper)
        new += result.new_in_project
        duplicates += not result.new_in_project
    db.finish_search_run(conn, run_id, status="completed", n_retrieved=len(papers),
                         n_new=new, n_duplicates=duplicates)
    summary = {"run_id": run_id, "retrieved": len(papers), "new": new, "duplicates": duplicates,
               "without_abstract": sum(not p.has_abstract for p in papers)}
    db.log_event(conn, project_id, "info", "search_completed", "OpenAlex search finished", summary)
    return summary


def run_screening(conn, project_id: int, provider, topic: str | None = None,
                  retry_failed: bool = False,
                  on_progress: Callable[[int, int, dict], None] | None = None) -> Counter:
    """Screen every paper that has no result yet for this topic and prompt version."""
    project = db.require_project(conn, project_id)
    topic = (topic or project["topic"]).strip()
    criteria_hash = topic_criteria_hash(topic)
    latest = db.latest_screenings(conn, project_id, criteria_hash)
    todo = [p for p in db.project_papers(conn, project_id)
            if p["id"] not in latest or (retry_failed and latest[p["id"]]["status"] == "failed")]
    db.log_event(conn, project_id, "info", "screening_started", f"Screening {len(todo)} papers",
                 {"provider": provider.name, "model": provider.model, "external": provider.is_external,
                  "topic": topic, "prompt_version": PROMPT_VERSION})
    counts: Counter = Counter()
    for index, row in enumerate(todo, start=1):
        outcome = screen_paper(db.paper_from_row(row), topic, provider)
        status = {"ok": "ok", "failed": "failed", "skipped_no_abstract": "skipped"}[outcome["screening_status"]]
        relevant = outcome["is_relevant"]
        decision = None if relevant is None else ("include" if relevant else "exclude")
        if status == "skipped":
            decision = "uncertain"
        db.add_screening(
            conn, project_id=project_id, paper_id=row["id"], status=status, decision=decision,
            reason=outcome["reason"], prompt_version=PROMPT_VERSION, criteria_hash=criteria_hash,
            provider=provider.name, model=provider.model, settings={"topic": topic},
            raw_response=outcome["raw_response"], error=outcome["screening_error"],
        )
        if status == "failed":
            db.log_event(conn, project_id, "warning", "screening_failed",
                         outcome["screening_error"] or "unknown error", {"paper_id": row["id"]})
        counts[status] += 1
        if on_progress:
            on_progress(index, len(todo), outcome)
    db.log_event(conn, project_id, "info", "screening_completed", "Screening finished", dict(counts))
    return counts
