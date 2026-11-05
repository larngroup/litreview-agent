"""Command-line interface.

Database workflow (new in Stage 3):
    litagent project create NAME --topic "..."
    litagent search "query" --project NAME --limit 100
    litagent screen --project NAME [--retry-failed]
    litagent status --project NAME
    litagent import-json --project NAME papers.json [--evaluated evaluated.json]

JSON workflow from Stage 2 (still works, no --project):
    litagent search "query" --out data/papers_dataset.json
    litagent screen data/papers_dataset.json --out data/evaluated_dataset.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from . import pipeline
from .config import load_settings
from .discovery.openalex import configure_pyalex, search_openalex
from .models import Paper, utc_now
from .providers.groq import GroqProvider, LLMError
from .screening.relevance import screen_papers
from .storage import database as db
from .storage.legacy_import import import_evaluated_json, import_papers_json


def _write_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _open_db(settings):
    return db.connect(settings.db_path)


def _make_provider(settings):
    provider = GroqProvider.from_settings(settings)
    if provider.is_external:
        print(f"NOTE: titles and abstracts will be sent to an external provider ({provider.name}).")
    return provider


# --------------------------------------------------------------------------- project

def cmd_project_create(args, settings) -> int:
    conn = _open_db(settings)
    project_id = db.create_project(conn, args.name, args.topic, args.question or "")
    print(f"Created project {args.name!r} (id {project_id}) in {settings.db_path}")
    return 0


def cmd_project_list(args, settings) -> int:
    conn = _open_db(settings)
    for project in db.list_projects(conn):
        count = conn.execute("SELECT COUNT(*) FROM project_papers WHERE project_id = ?",
                             (project["id"],)).fetchone()[0]
        print(f"{project['id']:>3}  {project['name']:<30} {count:>6} papers  topic: {project['topic']}")
    return 0


# --------------------------------------------------------------------------- search

def cmd_search(args, settings) -> int:
    configure_pyalex(settings.openalex_api_key, settings.contact_email)
    if not settings.openalex_api_key:
        print("WARNING: OPENALEX_API_KEY not set; OpenAlex allows only a small daily budget without a key.")
    if args.project:
        conn = _open_db(settings)
        project = db.require_project(conn, args.project)
        summary = pipeline.run_search(conn, project["id"], args.query, args.limit, search_fn=search_openalex)
        print(json.dumps(summary, indent=2))
        return 0

    started = utc_now()
    papers = search_openalex(args.query, limit=args.limit)
    out = Path(args.out)
    _write_json([p.model_dump(mode="json") for p in papers], out)
    run_log = {
        "source": "openalex", "query": args.query, "requested_limit": args.limit,
        "started_at": started.isoformat(), "finished_at": utc_now().isoformat(),
        "records": len(papers), "without_abstract": sum(not p.has_abstract for p in papers),
        "output_file": str(out),
    }
    _write_json(run_log, out.with_name(out.stem + "_search_run.json"))
    print(json.dumps(run_log, indent=2))
    return 0


# --------------------------------------------------------------------------- screen

def cmd_screen(args, settings) -> int:
    try:
        provider = _make_provider(settings)
    except LLMError as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.project:
        conn = _open_db(settings)
        project = db.require_project(conn, args.project)

        def progress(index: int, total: int, outcome: dict) -> None:
            title = (outcome.get("title") or "(no title)")[:60]
            print(f"[{index}/{total}] {outcome['screening_status']:<20} {title}")

        counts = pipeline.run_screening(conn, project["id"], provider, topic=args.topic,
                                        retry_failed=args.retry_failed, on_progress=progress)
        print("Summary:", dict(counts) or "nothing to screen")
        return 0

    if not args.input:
        print("ERROR: give an input JSON file or --project.")
        return 2
    papers = [Paper.model_validate(r) for r in _read_json(Path(args.input))]
    topic = args.topic
    if not topic:
        queries = {p.query for p in papers if p.query}
        if len(queries) != 1:
            print("ERROR: pass --topic (the file has zero or several different queries).")
            return 2
        topic = queries.pop()
    print(f"Screening {len(papers)} papers for topic: {topic!r}")

    def progress_json(index: int, outcome: dict) -> None:
        title = (outcome.get("title") or "(no title)")[:60]
        print(f"[{index}/{len(papers)}] {outcome['screening_status']:<20} {title}")

    results = screen_papers(papers, topic, provider, on_progress=progress_json)
    _write_json(results, Path(args.out))
    print("Summary:", dict(Counter(r["screening_status"] for r in results)))
    return 0


# --------------------------------------------------------------------------- status and import

def cmd_status(args, settings) -> int:
    conn = _open_db(settings)
    project = db.require_project(conn, args.project)
    papers = db.project_papers(conn, project["id"])
    statuses = Counter((p["screening"] or {}).get("status", "not screened") for p in papers)
    decisions = Counter((p["screening"] or {}).get("decision") or "-" for p in papers)
    print(f"Project {project['name']!r}  topic: {project['topic']}")
    print(f"Papers: {len(papers)}  (without abstract: {sum(not p['has_abstract'] for p in papers)})")
    print("Latest screening status:", dict(statuses))
    print("Model suggestions:      ", dict(decisions))
    print("Human-reviewed:         ", sum(p["review"] is not None for p in papers))
    for run in db.list_search_runs(conn, project["id"]):
        print(f"  run {run['id']}: {run['source']:<12} {run['status']:<10} {run['started_at']} "
              f"retrieved={run['n_retrieved']} new={run['n_new']} query={run['query']!r}")
    return 0


def cmd_import_json(args, settings) -> int:
    conn = _open_db(settings)
    project = db.get_project(conn, args.project)
    if project is None:
        topic = args.legacy_topic or args.query
        if not topic:
            print("ERROR: project does not exist; pass --legacy-topic so it can be created.")
            return 2
        db.create_project(conn, args.project, topic)
        project = db.require_project(conn, args.project)
        print(f"Created project {args.project!r}")
    summary = import_papers_json(conn, project["id"], args.papers, query=args.query or "")
    print("Papers:", summary)
    if args.evaluated:
        if not args.legacy_topic:
            print("ERROR: --legacy-topic is required with --evaluated (the v4 notebook used 'Human in the loop').")
            return 2
        print("Screenings:", import_evaluated_json(conn, project["id"], args.evaluated, args.legacy_topic))
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="litagent", description="Literature discovery and screening")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    project = sub.add_parser("project", help="create or list research projects")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    create = project_sub.add_parser("create")
    create.add_argument("name")
    create.add_argument("--topic", required=True)
    create.add_argument("--question", help="research question")
    create.set_defaults(func=cmd_project_create)
    project_sub.add_parser("list").set_defaults(func=cmd_project_list)

    search = sub.add_parser("search", help="search OpenAlex")
    search.add_argument("query")
    search.add_argument("--project", help="store results in this project (database)")
    search.add_argument("--limit", type=int, default=100)
    search.add_argument("--out", default="data/papers_dataset.json", help="JSON output (without --project)")
    search.set_defaults(func=cmd_search)

    screen = sub.add_parser("screen", help="screen papers with the LLM")
    screen.add_argument("input", nargs="?", help="JSON file (without --project)")
    screen.add_argument("--project")
    screen.add_argument("--topic", help="override the topic")
    screen.add_argument("--retry-failed", action="store_true", help="re-run failed screenings")
    screen.add_argument("--out", default="data/evaluated_dataset.json")
    screen.set_defaults(func=cmd_screen)

    status = sub.add_parser("status", help="show a project summary")
    status.add_argument("--project", required=True)
    status.set_defaults(func=cmd_status)

    imp = sub.add_parser("import-json", help="import JSON files from the notebook")
    imp.add_argument("papers", help="papers_dataset.json")
    imp.add_argument("--project", required=True)
    imp.add_argument("--evaluated", help="evaluated_dataset.json")
    imp.add_argument("--legacy-topic", help="topic the old screening used")
    imp.add_argument("--query", help="query used for the old search, if known")
    imp.set_defaults(func=cmd_import_json)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")
    try:
        return args.func(args, load_settings())
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
