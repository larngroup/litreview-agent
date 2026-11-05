"""SQLite storage for projects, search runs, papers, provenance, screening and logs.

Design rules
------------
* A row in `papers` is the *merged* view of one publication.
* Every record exactly as a source returned it is kept in `paper_sources`
  (provenance). Nothing a source said is ever thrown away.
* When a second source describes a known paper, only EMPTY fields of the merged
  row are filled in. Existing values are never overwritten; disagreements are
  reported by `find_conflicts()` for a human to resolve.
* Model screening results (`screenings`) and human decisions (`reviews`) are
  separate tables, so the model's suggestion can never silently become the
  final decision.
* Full-text files are NOT stored here; Stage 8 adds a separate table for them.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Paper, title_key, utc_now

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT NOT NULL,
    research_question TEXT NOT NULL DEFAULT '',
    inclusion_criteria TEXT NOT NULL DEFAULT '[]',
    exclusion_criteria TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    requested_limit INTEGER,
    parameters TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    n_retrieved INTEGER NOT NULL DEFAULT 0,
    n_new INTEGER NOT NULL DEFAULT 0,
    n_duplicates INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    doi TEXT UNIQUE,
    title TEXT,
    title_key TEXT,
    year INTEGER,
    authors TEXT NOT NULL DEFAULT '[]',
    keywords TEXT NOT NULL DEFAULT '[]',
    abstract TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_papers_title_key ON papers(title_key);

CREATE TABLE IF NOT EXISTS paper_sources (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_id TEXT,
    search_run_id INTEGER REFERENCES search_runs(id) ON DELETE SET NULL,
    retrieved_at TEXT NOT NULL,
    record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sources_lookup ON paper_sources(source, source_id);
CREATE INDEX IF NOT EXISTS idx_sources_paper ON paper_sources(paper_id);

CREATE TABLE IF NOT EXISTS project_papers (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    first_search_run_id INTEGER REFERENCES search_runs(id) ON DELETE SET NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (project_id, paper_id)
);

CREATE TABLE IF NOT EXISTS screenings (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'skipped')),
    decision TEXT CHECK (decision IN ('include', 'exclude', 'uncertain')),
    reason TEXT,
    details TEXT NOT NULL DEFAULT '{}',
    provider TEXT,
    model TEXT,
    prompt_version TEXT NOT NULL,
    criteria_hash TEXT NOT NULL,
    settings TEXT NOT NULL DEFAULT '{}',
    raw_response TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_screenings_lookup ON screenings(project_id, paper_id, criteria_hash);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('include', 'exclude', 'uncertain')),
    note TEXT NOT NULL DEFAULT '',
    reviewer TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK (level IN ('info', 'warning', 'error')),
    event TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return utc_now().isoformat()


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def connect(path: str | Path) -> sqlite3.Connection:
    """Open (and if needed create) the database. Use ':memory:' in tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    with conn:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT version FROM schema_info").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_info (version) VALUES (?)", (SCHEMA_VERSION,))
        elif row["version"] > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {row['version']} is newer than this code "
                f"supports ({SCHEMA_VERSION}). Update the application."
            )
    return conn


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


# --------------------------------------------------------------------------- projects

def create_project(conn, name: str, topic: str, research_question: str = "",
                   inclusion_criteria: list[str] | None = None,
                   exclusion_criteria: list[str] | None = None) -> int:
    name, topic = (name or "").strip(), (topic or "").strip()
    if not name or not topic:
        raise ValueError("A project needs a name and a topic.")
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO projects (name, topic, research_question, inclusion_criteria, "
                "exclusion_criteria, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, topic, research_question.strip(), _dumps(inclusion_criteria or []),
                 _dumps(exclusion_criteria or []), _now()),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"A project called {name!r} already exists.") from exc
    return cursor.lastrowid


def _project_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    data["inclusion_criteria"] = json.loads(data["inclusion_criteria"])
    data["exclusion_criteria"] = json.loads(data["exclusion_criteria"])
    return data


def get_project(conn, name_or_id: str | int) -> dict | None:
    if isinstance(name_or_id, int):
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (name_or_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM projects WHERE name = ?", (name_or_id,)).fetchone()
    return _project_dict(row)


def require_project(conn, name_or_id: str | int) -> dict:
    project = get_project(conn, name_or_id)
    if project is None:
        raise ValueError(f"Project {name_or_id!r} not found. Create it first.")
    return project


def list_projects(conn) -> list[dict]:
    return [_project_dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY id")]


def update_project(conn, project_id: int, *, topic: str, research_question: str,
                   inclusion_criteria: list[str], exclusion_criteria: list[str]) -> None:
    if not (topic or "").strip():
        raise ValueError("The topic cannot be empty.")
    with conn:
        conn.execute(
            "UPDATE projects SET topic = ?, research_question = ?, inclusion_criteria = ?, "
            "exclusion_criteria = ? WHERE id = ?",
            (topic.strip(), research_question.strip(),
             _dumps([c.strip() for c in inclusion_criteria if c.strip()]),
             _dumps([c.strip() for c in exclusion_criteria if c.strip()]), project_id),
        )


# --------------------------------------------------------------------------- search runs

def start_search_run(conn, project_id: int, source: str, query: str,
                     requested_limit: int | None, parameters: dict | None = None) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO search_runs (project_id, source, query, requested_limit, parameters, "
            "status, started_at) VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (project_id, source, query, requested_limit, _dumps(parameters or {}), _now()),
        )
    return cursor.lastrowid


def finish_search_run(conn, run_id: int, *, status: str, n_retrieved: int = 0, n_new: int = 0,
                      n_duplicates: int = 0, error: str | None = None) -> None:
    with conn:
        conn.execute(
            "UPDATE search_runs SET status = ?, finished_at = ?, n_retrieved = ?, n_new = ?, "
            "n_duplicates = ?, error = ? WHERE id = ?",
            (status, _now(), n_retrieved, n_new, n_duplicates, error, run_id),
        )


def list_search_runs(conn, project_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM search_runs WHERE project_id = ? ORDER BY id", (project_id,))
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- papers

@dataclass(frozen=True)
class AddResult:
    paper_id: int
    new_paper: bool        # a new row was created in `papers`
    new_in_project: bool   # the paper was not yet part of this project
    matched_by: str | None # 'doi' | 'source_id' | 'title' | None


def find_existing_paper(conn, paper: Paper) -> tuple[int | None, str | None]:
    """Return (paper_id, rule) for an existing record describing the same publication."""
    if paper.doi:
        row = conn.execute("SELECT id FROM papers WHERE doi = ?", (paper.doi,)).fetchone()
        if row:
            return row["id"], "doi"
    if paper.source_id:
        row = conn.execute(
            "SELECT paper_id FROM paper_sources WHERE source = ? AND source_id = ? LIMIT 1",
            (paper.source, paper.source_id),
        ).fetchone()
        if row:
            return row["paper_id"], "source_id"
    key = paper.title_key
    if key:
        candidates = [
            r for r in conn.execute("SELECT id, year, doi FROM papers WHERE title_key = ?", (key,))
            # Same title is only accepted when years agree (or one is missing) and the
            # two records do not carry DIFFERENT DOIs (e.g. preprint vs journal version).
            if (r["year"] is None or paper.year is None or r["year"] == paper.year)
            and (r["doi"] is None or paper.doi is None)
        ]
        if len(candidates) == 1:           # ambiguous matches are NOT merged
            return candidates[0]["id"], "title"
    return None, None


def add_paper(conn, project_id: int, search_run_id: int | None, paper: Paper) -> AddResult:
    """Insert or merge `paper`, record its provenance, and link it to the project."""
    now = _now()
    with conn:
        paper_id, matched_by = find_existing_paper(conn, paper)
        new_paper = paper_id is None
        if new_paper:
            cursor = conn.execute(
                "INSERT INTO papers (doi, title, title_key, year, authors, keywords, abstract, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (paper.doi, paper.title, paper.title_key, paper.year, _dumps(paper.authors),
                 _dumps(paper.keywords), paper.abstract, now, now),
            )
            paper_id = cursor.lastrowid
        else:
            _fill_missing_fields(conn, paper_id, paper, now)

        conn.execute(
            "INSERT INTO paper_sources (paper_id, source, source_id, search_run_id, retrieved_at, "
            "record_json) VALUES (?, ?, ?, ?, ?, ?)",
            (paper_id, paper.source, paper.source_id, search_run_id,
             paper.retrieved_at.isoformat(), _dumps(paper.model_dump(mode="json"))),
        )
        cursor = conn.execute(
            "INSERT OR IGNORE INTO project_papers (project_id, paper_id, first_search_run_id, added_at) "
            "VALUES (?, ?, ?, ?)",
            (project_id, paper_id, search_run_id, now),
        )
        new_in_project = cursor.rowcount == 1
    return AddResult(paper_id, new_paper, new_in_project, matched_by)


def _fill_missing_fields(conn, paper_id: int, paper: Paper, now: str) -> None:
    """Fill only EMPTY fields of the merged row. Never overwrite existing values."""
    current = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    updates: dict[str, Any] = {}
    if current["title"] is None and paper.title:
        updates["title"], updates["title_key"] = paper.title, paper.title_key
    if current["year"] is None and paper.year:
        updates["year"] = paper.year
    if not current["abstract"] and paper.abstract:
        updates["abstract"] = paper.abstract
    if current["authors"] == "[]" and paper.authors:
        updates["authors"] = _dumps(paper.authors)
    if current["keywords"] == "[]" and paper.keywords:
        updates["keywords"] = _dumps(paper.keywords)
    if current["doi"] is None and paper.doi:
        taken = conn.execute("SELECT 1 FROM papers WHERE doi = ?", (paper.doi,)).fetchone()
        if not taken:   # if another row owns this DOI, leave it for find_conflicts/human review
            updates["doi"] = paper.doi
    if updates:
        updates["updated_at"] = now
        assignments = ", ".join(f"{column} = ?" for column in updates)
        conn.execute(f"UPDATE papers SET {assignments} WHERE id = ?", (*updates.values(), paper_id))


def _paper_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["authors"] = json.loads(data["authors"])
    data["keywords"] = json.loads(data["keywords"])
    data["has_abstract"] = bool(data["abstract"])
    return data


def get_paper(conn, paper_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return _paper_dict(row) if row else None


def paper_from_row(row: dict, query: str = "") -> Paper:
    """Rebuild a Paper (merged view) from a `papers` row, e.g. for screening."""
    return Paper(source="merged", source_id=str(row["id"]), doi=row["doi"], title=row["title"],
                 year=row["year"], authors=row["authors"], keywords=row["keywords"],
                 abstract=row["abstract"], query=query)


def get_paper_sources(conn, paper_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM paper_sources WHERE paper_id = ? ORDER BY id", (paper_id,))
    result = []
    for row in rows:
        data = dict(row)
        data["record"] = json.loads(data.pop("record_json"))
        result.append(data)
    return result


def find_conflicts(conn, paper_id: int) -> dict[str, list]:
    """Fields on which the sources of one paper disagree, e.g. {'year': [2020, 2021]}."""
    values: dict[str, set] = {"doi": set(), "title": set(), "year": set()}
    titles: dict[str, str] = {}
    for source in get_paper_sources(conn, paper_id):
        record = source["record"]
        if record.get("doi"):
            values["doi"].add(record["doi"])
        if record.get("year"):
            values["year"].add(record["year"])
        key = title_key(record.get("title"))
        if key:
            titles.setdefault(key, record["title"])
    values["title"] = set(titles.values())
    return {field: sorted(found, key=str) for field, found in values.items() if len(found) > 1}


# --------------------------------------------------------------------------- screening and review

def add_screening(conn, *, project_id: int, paper_id: int, status: str, decision: str | None,
                  reason: str | None, prompt_version: str, criteria_hash: str,
                  provider: str | None = None, model: str | None = None,
                  details: dict | None = None, settings: dict | None = None,
                  raw_response: str | None = None, error: str | None = None,
                  created_at: str | None = None) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO screenings (project_id, paper_id, status, decision, reason, details, provider, "
            "model, prompt_version, criteria_hash, settings, raw_response, error, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, paper_id, status, decision, reason, _dumps(details or {}), provider, model,
             prompt_version, criteria_hash, _dumps(settings or {}), raw_response, error,
             created_at or _now()),
        )
    return cursor.lastrowid


def latest_screenings(conn, project_id: int, criteria_hash: str | None = None) -> dict[int, dict]:
    """Most recent screening per paper (optionally only for one set of criteria)."""
    sql = ("SELECT * FROM screenings WHERE id IN (SELECT MAX(id) FROM screenings "
           "WHERE project_id = ?{extra} GROUP BY paper_id)")
    params: list[Any] = [project_id]
    extra = ""
    if criteria_hash is not None:
        extra = " AND criteria_hash = ?"
        params.append(criteria_hash)
    rows = conn.execute(sql.format(extra=extra), params)
    result = {}
    for row in rows:
        data = dict(row)
        data["details"] = json.loads(data["details"])
        data["settings"] = json.loads(data["settings"])
        result[data["paper_id"]] = data
    return result


def add_review(conn, project_id: int, paper_id: int, decision: str,
               note: str = "", reviewer: str = "") -> int:
    if decision not in ("include", "exclude", "uncertain"):
        raise ValueError("decision must be include, exclude or uncertain")
    with conn:
        cursor = conn.execute(
            "INSERT INTO reviews (project_id, paper_id, decision, note, reviewer, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, paper_id, decision, note.strip(), reviewer.strip(), _now()),
        )
    return cursor.lastrowid


def latest_reviews(conn, project_id: int) -> dict[int, dict]:
    rows = conn.execute(
        "SELECT * FROM reviews WHERE id IN (SELECT MAX(id) FROM reviews WHERE project_id = ? "
        "GROUP BY paper_id)", (project_id,))
    return {r["paper_id"]: dict(r) for r in rows}


def project_papers(conn, project_id: int, criteria_hash: str | None = None) -> list[dict]:
    """Every paper of a project with its latest model screening and latest human review."""
    screenings = latest_screenings(conn, project_id, criteria_hash)
    reviews = latest_reviews(conn, project_id)
    rows = conn.execute(
        "SELECT p.* FROM papers p JOIN project_papers pp ON pp.paper_id = p.id "
        "WHERE pp.project_id = ? ORDER BY p.id", (project_id,))
    result = []
    for row in rows:
        paper = _paper_dict(row)
        paper["screening"] = screenings.get(paper["id"])
        paper["review"] = reviews.get(paper["id"])
        # The FINAL decision is always the human one. The model only suggests.
        paper["final_decision"] = paper["review"]["decision"] if paper["review"] else None
        result.append(paper)
    return result


# --------------------------------------------------------------------------- events (execution log)

def log_event(conn, project_id: int | None, level: str, event: str, message: str,
              details: dict | None = None) -> None:
    with conn:
        conn.execute(
            "INSERT INTO events (project_id, level, event, message, details, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, level, event, message, _dumps(details or {}), _now()),
        )


def list_events(conn, project_id: int, limit: int = 200) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM events WHERE project_id = ? ORDER BY id DESC LIMIT ?", (project_id, limit))
    return [dict(r) for r in rows]
