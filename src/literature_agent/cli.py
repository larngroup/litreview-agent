"""Command-line interface.

    litagent project create NAME --topic "..." [--question "..."]
    litagent project criteria NAME --include "..." --exclude "..." [--question "..."]
    litagent project list
    litagent search "query" --project NAME [--source openalex --source crossref] [--limit 100]
    litagent screen --project NAME [--provider groq|ollama] [--model M] [--retry-failed] [--redo] [--max N]
    litagent review --project NAME --paper ID --decision include|exclude|uncertain [--note "..."]
    litagent papers --project NAME [--decision uncertain] [--unreviewed]
    litagent failures --project NAME
    litagent evaluate --project NAME
    litagent status --project NAME
    litagent import-json --project NAME papers.json [--evaluated evaluated.json --legacy-topic "..."]

`search` without --project still writes a JSON file (Stage 2 behaviour).
Screening of JSON files was removed in Stage 5: import them with `import-json`.
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
from .discovery import SOURCE_NAMES, make_source
from .models import utc_now
#from .providers.groq import GroqProvider, LLMError
from .providers import PROVIDER_NAMES, LLMError, get_provider
from .screening.evaluation import agreement_report
from .screening.relevance import Criteria
from .storage import database as db
from .storage.legacy_import import import_evaluated_json, import_papers_json

DECISIONS = ("include", "exclude", "uncertain")


def _write_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _open_db(settings):
    return db.connect(settings.db_path)


def _make_provider(settings, name=None, model=None):
    provider = get_provider(settings, name=name, model=model)
    if provider.is_external:
        print(f"NOTE: titles and abstracts will be sent to an external provider ({provider.name}).")
    else:
        print(f"Using local model {provider.model!r} via {provider.name}; data stays on this computer.")
    return provider


def _project(conn, name):
    return db.require_project(conn, name)


# --------------------------------------------------------------------------- project

def cmd_project_create(args, settings) -> int:
    conn = _open_db(settings)
    project_id = db.create_project(conn, args.name, args.topic, args.question or "",
                                   args.include or [], args.exclude or [])
    print(f"Created project {args.name!r} (id {project_id}) in {settings.db_path}")
    return 0


def cmd_project_criteria(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.name)
    db.update_project(
        conn, project["id"],
        topic=args.topic or project["topic"],
        research_question=args.question if args.question is not None else project["research_question"],
        inclusion_criteria=args.include if args.include is not None else project["inclusion_criteria"],
        exclusion_criteria=args.exclude if args.exclude is not None else project["exclusion_criteria"],
    )
    updated = _project(conn, args.name)
    db.log_event(conn, project["id"], "info", "criteria_updated", "Screening criteria changed",
                 {k: updated[k] for k in ("topic", "research_question", "inclusion_criteria",
                                          "exclusion_criteria")})
    print(json.dumps({k: updated[k] for k in ("topic", "research_question", "inclusion_criteria",
                                              "exclusion_criteria")}, indent=2))
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
    source_names = args.source or ["openalex"]
    if "openalex" in source_names and not settings.openalex_api_key:
        print("WARNING: OPENALEX_API_KEY not set; OpenAlex allows only a small daily budget without a key.")
    if "crossref" in source_names and not settings.contact_email:
        print("WARNING: CONTACT_EMAIL not set; Crossref will use its slower public pool.")
    sources = [make_source(name, settings) for name in source_names]
    if args.project:
        conn = _open_db(settings)
        project = _project(conn, args.project)
        summaries = pipeline.run_multi_search(conn, project["id"], args.query, args.limit, sources)
        print(json.dumps(summaries, indent=2))
        return 1 if any("error" in s for s in summaries) else 0

    started = utc_now()
    papers = [paper for source in sources for paper in source.search(args.query, limit=args.limit)]
    out = Path(args.out)
    _write_json([p.model_dump(mode="json") for p in papers], out)
    run_log = {
        "sources": source_names, "query": args.query, "requested_limit_per_source": args.limit,
        "started_at": started.isoformat(), "finished_at": utc_now().isoformat(),
        "records": len(papers), "without_abstract": sum(not p.has_abstract for p in papers),
        "output_file": str(out),
    }
    _write_json(run_log, out.with_name(out.stem + "_search_run.json"))
    print(json.dumps(run_log, indent=2))
    return 0


# --------------------------------------------------------------------------- screening

def cmd_screen(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.project)
    if not project["inclusion_criteria"]:
        print("WARNING: no inclusion criteria set; the model will judge against the topic only. "
              "Use `litagent project criteria`.")
    try:
        provider = _make_provider(settings, name=args.provider, model=args.model)
    except LLMError as exc:
        print(f"ERROR: {exc}")
        return 2

    def progress(index: int, total: int, result) -> None:
        print(f"[{index}/{total}] {result.status:<8} {result.decision or '-':<10} {(result.reason or result.error or '')[:70]}")

    counts = pipeline.run_screening(conn, project["id"], provider, retry_failed=args.retry_failed,
                                    redo_all=args.redo, max_papers=args.max, on_progress=progress)
    print("Summary:", dict(counts) or "nothing to screen")
    if counts.get("failed"):
        print("Some screenings failed. Inspect them with `litagent failures`, then run with --retry-failed.")
    return 0


def cmd_review(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.project)
    member = conn.execute("SELECT 1 FROM project_papers WHERE project_id = ? AND paper_id = ?",
                          (project["id"], args.paper)).fetchone()
    if not member:
        print(f"ERROR: paper {args.paper} is not part of project {project['name']!r}.")
        return 2
    db.add_review(conn, project["id"], args.paper, args.decision, args.note or "", args.reviewer or "")
    print(f"Recorded human decision {args.decision!r} for paper {args.paper}.")
    return 0


def cmd_papers(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.project)
    criteria_hash = Criteria.from_project(project).fingerprint()
    for paper in db.project_papers(conn, project["id"], criteria_hash):
        suggestion = (paper["screening"] or {}).get("decision")
        final = paper["final_decision"]
        if args.decision and suggestion != args.decision:
            continue
        if args.unreviewed and final is not None:
            continue
        
        # Display abstract, DOI and article URL if available - changed at stage 5
        
        doi = paper.get("doi")
        source_id = paper.get("source_id")
        abstract = paper.get("abstract") or ""

        doi_url = f"https://doi.org/{doi}" if doi else None
        article_url = doi_url or source_id

        has_abstract = bool(abstract.strip())

        print(
            f"\nPaper #{paper['id']}"
            f"\nTitle: {paper.get('title') or '(no title)'}"
            f"\nDOI: {doi or 'Not available'}"
            f"\nLink: {article_url or 'Not available'}"
            f"\nAbstract (database): {'YES' if has_abstract else 'NO'}"
            f"\nLLM decision: {suggestion or 'pending'}"
            f"\nHuman decision: {final or 'pending'}"
        )


    return 0


def cmd_failures(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.project)
    criteria_hash = Criteria.from_project(project).fingerprint()
    failed = [s for s in db.latest_screenings(conn, project["id"], criteria_hash).values()
              if s["status"] == "failed"]
    for item in failed:
        print(f"paper {item['paper_id']}: {item['error']}")
        if item["raw_response"]:
            print(f"    raw: {item['raw_response'][:200]!r}")
    print(f"{len(failed)} failed screening(s).")
    return 0


def cmd_evaluate(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.project)
    criteria_hash = Criteria.from_project(project).fingerprint()
    report = agreement_report(db.project_papers(conn, project["id"], criteria_hash))
    print(json.dumps(report, indent=2))
    if report["compared"] < 30:
        print("NOTE: fewer than 30 human-reviewed papers; these numbers are not yet meaningful.")
    return 0


# --------------------------------------------------------------------------- status and import

def cmd_status(args, settings) -> int:
    conn = _open_db(settings)
    project = _project(conn, args.project)
    criteria_hash = Criteria.from_project(project).fingerprint()
    papers = db.project_papers(conn, project["id"], criteria_hash)
    statuses = Counter((p["screening"] or {}).get("status", "not screened") for p in papers)
    suggestions = Counter((p["screening"] or {}).get("decision") or "-" for p in papers)
    finals = Counter(p["final_decision"] or "not reviewed" for p in papers)
    print(f"Project {project['name']!r}  topic: {project['topic']}")
    print(f"Papers: {len(papers)}  (without abstract: {sum(not p['has_abstract'] for p in papers)})")
    print("Screening status (current criteria):", dict(statuses))
    print("Model suggestions:                  ", dict(suggestions))
    print("Human decisions:                    ", dict(finals))
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
        project = _project(conn, args.project)
        print(f"Created project {args.project!r}")
    print("Papers:", import_papers_json(conn, project["id"], args.papers, query=args.query or ""))
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

    project = sub.add_parser("project", help="create, configure or list research projects")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    create = project_sub.add_parser("create")
    create.add_argument("name")
    create.add_argument("--topic", required=True)
    create.add_argument("--question", help="research question")
    create.add_argument("--include", action="append", help="inclusion criterion (repeatable)")
    create.add_argument("--exclude", action="append", help="exclusion criterion (repeatable)")
    create.set_defaults(func=cmd_project_create)
    criteria = project_sub.add_parser("criteria", help="replace topic/question/criteria")
    criteria.add_argument("name")
    criteria.add_argument("--topic")
    criteria.add_argument("--question")
    criteria.add_argument("--include", action="append")
    criteria.add_argument("--exclude", action="append")
    criteria.set_defaults(func=cmd_project_criteria)
    project_sub.add_parser("list").set_defaults(func=cmd_project_list)

    search = sub.add_parser("search", help="search scholarly sources")
    search.add_argument("query")
    search.add_argument("--source", action="append", choices=SOURCE_NAMES,
                        help="repeat to use several sources (default: openalex)")
    search.add_argument("--project", help="store results in this project (database)")
    search.add_argument("--limit", type=int, default=100, help="maximum records per source")
    search.add_argument("--out", default="data/papers_dataset.json", help="JSON output (without --project)")
    search.set_defaults(func=cmd_search)

    screen = sub.add_parser("screen", help="screen the project's papers with the LLM")
    screen.add_argument("--project", required=True)
    screen.add_argument("--retry-failed", action="store_true", help="re-run failed screenings")
    screen.add_argument("--redo", action="store_true", help="re-screen every paper")
    screen.add_argument("--max", type=int, help="screen at most N papers (useful for a trial run)")
    screen.add_argument("--provider", choices=PROVIDER_NAMES, help="override LLM_PROVIDER")
    screen.add_argument("--model", help="override the model name")
    screen.set_defaults(func=cmd_screen)

    review = sub.add_parser("review", help="record a human screening decision")
    review.add_argument("--project", required=True)
    review.add_argument("--paper", type=int, required=True, help="paper id (see `litagent papers`)")
    review.add_argument("--decision", choices=DECISIONS, required=True)
    review.add_argument("--note")
    review.add_argument("--reviewer")
    review.set_defaults(func=cmd_review)

    papers = sub.add_parser("papers", help="list papers with model and human decisions")
    papers.add_argument("--project", required=True)
    papers.add_argument("--decision", choices=DECISIONS, help="filter on the model suggestion")
    papers.add_argument("--unreviewed", action="store_true", help="only papers without a human decision")
    papers.set_defaults(func=cmd_papers)

    failures = sub.add_parser("failures", help="show failed screenings with their errors")
    failures.add_argument("--project", required=True)
    failures.set_defaults(func=cmd_failures)

    evaluate = sub.add_parser("evaluate", help="compare model suggestions with human decisions")
    evaluate.add_argument("--project", required=True)
    evaluate.set_defaults(func=cmd_evaluate)

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
    
    # Silence httpx and httpcore debug logs, which are showing API keys in the logs. - added at stage 4
    #logging.getLogger("httpx").setLevel(logging.WARNING)
    #logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    try:
        return args.func(args, load_settings())
    except KeyboardInterrupt:
        print("\nSearch or screening interrupted by user (Ctrl+C).")    #added at stage 3
        return 130
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
