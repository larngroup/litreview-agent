"""Import the JSON files produced by the original notebook (v4) and by Stage 1/2.

Nothing is deleted or rewritten: the JSON files stay where they are, and every
imported record is stored with its original content in `paper_sources`.

stage 5 - Legacy screening imports distinguish records skipped due to missing abstracts
from genuine processing failures, preserving the original evaluation outcome.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..models import Paper, normalise_doi, title_key
from . import database as db

# Placeholder strings written by the v4 notebook instead of real missing values.
_FAKE_TITLES = {"no title available"}
_FAKE_ABSTRACTS = {"abstract not available"}
LEGACY_PROMPT_VERSION = "legacy-v4"


def _read_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ValueError(f"{path} must contain a JSON list of objects.")
    return data


def legacy_record_to_paper(record: dict, default_query: str, retrieved_at: datetime) -> Paper:
    source_id = record.get("source_id") or record.get("id")
    title = record.get("title")
    if isinstance(title, str) and title.strip().lower() in _FAKE_TITLES:
        title = None
    abstract = record.get("abstract")
    if isinstance(abstract, str) and abstract.strip().lower() in _FAKE_ABSTRACTS:
        abstract = ""
    if record.get("source"):
        source = record["source"]
    elif isinstance(source_id, str) and source_id.startswith("https://openalex.org/"):
        source = "openalex"
    else:
        source = "legacy_json"
    return Paper(
        source=source, source_id=source_id, doi=record.get("doi"), title=title,
        year=record.get("year"), authors=record.get("authors") or [],
        keywords=[k for k in record.get("keywords") or [] if isinstance(k, str)],
        abstract=abstract or "", query=record.get("query") or default_query,
        retrieved_at=record.get("retrieved_at") or retrieved_at,
    )


def import_papers_json(conn, project_id: int, path: str | Path, query: str = "") -> dict:
    path = Path(path)
    records = _read_list(path)
    # The v4 files have no retrieval date; the file's modification time is the best evidence.
    file_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0)
    run_query = query or next((r.get("query") for r in records if r.get("query")), "") or "(unknown - legacy import)"
    run_id = db.start_search_run(conn, project_id, "legacy_json", run_query, None, {
        "imported_file": str(path), "file_modified_at": file_time.isoformat(),
        "note": "Retrieval date unknown for v4 files; file modification time used instead.",
    })
    new = duplicates = 0
    for record in records:
        result = db.add_paper(conn, project_id, run_id, legacy_record_to_paper(record, run_query, file_time))
        new += result.new_in_project
        duplicates += not result.new_in_project
    db.finish_search_run(conn, run_id, status="completed", n_retrieved=len(records),
                         n_new=new, n_duplicates=duplicates)
    db.log_event(conn, project_id, "info", "legacy_import",
                 f"Imported {len(records)} records from {path.name}", {"run_id": run_id})
    return {"run_id": run_id, "records": len(records), "new": new, "duplicates": duplicates}


def _match_paper_id(conn, project_id: int, record: dict) -> int | None:
    source_id = record.get("source_id") or record.get("id")
    if source_id:
        row = conn.execute(
            "SELECT ps.paper_id FROM paper_sources ps JOIN project_papers pp ON pp.paper_id = ps.paper_id "
            "WHERE pp.project_id = ? AND ps.source_id = ? LIMIT 1", (project_id, source_id)).fetchone()
        if row:
            return row["paper_id"]
    doi = normalise_doi(record.get("doi"))
    if doi:
        row = conn.execute(
            "SELECT p.id FROM papers p JOIN project_papers pp ON pp.paper_id = p.id "
            "WHERE pp.project_id = ? AND p.doi = ?", (project_id, doi)).fetchone()
        if row:
            return row["id"]
    key = title_key(record.get("title"))
    if key:
        rows = conn.execute(
            "SELECT p.id FROM papers p JOIN project_papers pp ON pp.paper_id = p.id "
            "WHERE pp.project_id = ? AND p.title_key = ?", (project_id, key)).fetchall()
        if len(rows) == 1:
            return rows[0]["id"]
    return None


def import_evaluated_json(conn, project_id: int, path: str | Path, legacy_topic: str,
                          legacy_model: str = "openai/gpt-oss-20b") -> dict:
    """Import old screening results. They are marked 'legacy' so they are never
    confused with screenings made with the current prompt and criteria."""
    path = Path(path)
    imported = unmatched = 0
    for record in _read_list(path):
        paper_id = _match_paper_id(conn, project_id, record)
        if paper_id is None:
            unmatched += 1
            continue
        relevant = record.get("is_relevant")
        ok = isinstance(relevant, bool)

        legacy_status = str(record.get("status") or "").strip().lower()
        reason = str(record.get("reason") or "").strip()

        if ok:
            status = "ok"
            decision = "include" if relevant else "exclude"
            error = None

        elif legacy_status == "skipped_no_abstract":
            status = "skipped"
            decision = "uncertain"
            error = None

        else:
            status = "failed"
            decision = None
            error = reason or "Legacy record without a valid is_relevant value"

        db.add_screening(
            conn, project_id=project_id, paper_id=paper_id,
            status=status,
            decision=decision,
            reason=record.get("reason"),
            prompt_version=record.get("screening_prompt_version") or LEGACY_PROMPT_VERSION,
            criteria_hash="legacy",
            provider="groq", model=record.get("screening_model") or legacy_model,
            settings={"topic": record.get("screening_topic") or legacy_topic, "imported_from": str(path)},
            error=error,
        )
        imported += 1
    db.log_event(conn, project_id, "info", "legacy_import",
                 f"Imported {imported} legacy screenings from {path.name} ({unmatched} unmatched)")
    return {"imported": imported, "unmatched": unmatched}
