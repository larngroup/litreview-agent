"""Command-line interface: `litagent search ...` and `litagent screen ...`."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from .config import load_settings
from .discovery.openalex import configure_pyalex, search_openalex
from .models import Paper, utc_now
from .providers.groq import GroqProvider, LLMError
from .screening.relevance import screen_papers


def _write_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_search(args, settings) -> int:
    configure_pyalex(settings.openalex_api_key, settings.contact_email)
    if not settings.openalex_api_key:
        print("WARNING: OPENALEX_API_KEY not set; OpenAlex allows only a small daily budget without a key.")
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


def cmd_screen(args, settings) -> int:
    records = _read_json(Path(args.input))
    papers = [Paper.model_validate(r) for r in records]
    topic = args.topic
    if not topic:
        queries = {p.query for p in papers if p.query}
        if len(queries) != 1:
            print("ERROR: pass --topic (the file has zero or several different queries).")
            return 2
        topic = queries.pop()
    try:
        provider = GroqProvider.from_settings(settings)
    except LLMError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"Screening {len(papers)} papers for topic: {topic!r}")
    print(f"NOTE: titles and abstracts will be sent to an external provider ({provider.name}).")

    def progress(index: int, outcome: dict) -> None:
        title = (outcome.get("title") or "(no title)")[:60]
        print(f"[{index}/{len(papers)}] {outcome['screening_status']:<20} {title}")

    results = screen_papers(papers, topic, provider, on_progress=progress)
    _write_json(results, Path(args.out))
    print("Summary:", dict(Counter(r["screening_status"] for r in results)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="litagent", description="Literature discovery and screening")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="search OpenAlex and save papers to JSON")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=100)
    search.add_argument("--out", default="data/papers_dataset.json")
    search.set_defaults(func=cmd_search)

    screen = sub.add_parser("screen", help="screen a JSON file of papers with the LLM")
    screen.add_argument("input")
    screen.add_argument("--topic", help="research topic (default: the query stored in the file)")
    screen.add_argument("--out", default="data/evaluated_dataset.json")
    screen.set_defaults(func=cmd_screen)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    try:
        return args.func(args, load_settings())
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
