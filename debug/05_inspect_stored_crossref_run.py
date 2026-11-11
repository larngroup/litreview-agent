"""Inspect the Crossref records stored as provenance for a specific search run.

By default chooses the latest completed Crossref run for the given project.
Alternatively, --run-id can inspect an older run (for example run 21 or 22).
Reads paper_sources.record_json, which preserves the original per-source Paper
records, rather than the merged abstract stored in papers.
"""

import argparse
import json
from literature_agent.config import load_settings
from literature_agent.storage import database as db

parser = argparse.ArgumentParser()
parser.add_argument("--project", default="stage4-validation")
parser.add_argument("--run-id", type=int)
args = parser.parse_args()

conn = db.connect(load_settings().db_path)
try:
    project = db.require_project(conn, args.project)
    run_id = args.run_id
    if run_id is None:
        run = conn.execute(
            """SELECT id FROM search_runs
               WHERE project_id = ? AND source = 'crossref' AND status = 'completed'
               ORDER BY id DESC LIMIT 1""",
            (project["id"],),
        ).fetchone()
        if run is None:
            raise SystemExit("No completed Crossref run found for this project")
        run_id = run["id"]
    else:
        run = conn.execute(
            "SELECT id FROM search_runs WHERE id = ? AND project_id = ? AND source = 'crossref'",
            (run_id, project["id"]),
        ).fetchone()
        if run is None:
            raise SystemExit("Run ID is not a Crossref run in the selected project")

    rows = conn.execute(
        "SELECT record_json FROM paper_sources WHERE search_run_id = ? AND source = 'crossref' ORDER BY id",
        (run_id,),
    ).fetchall()
    print("Crossref run:", run_id)
    missing = 0
    for i, row in enumerate(rows, 1):
        paper = json.loads(row["record_json"])
        abstract = paper.get("abstract") or ""
        missing += not bool(abstract)
        print(f"\n{i}. {paper.get('title')}")
        print("DOI:", paper.get("doi"))
        print("Abstract length:", len(abstract))
    print("\nTotal:", len(rows))
    print("Without abstract:", missing)
finally:
    conn.close()
