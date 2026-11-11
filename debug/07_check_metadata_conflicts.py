"""Inspect disagreements between provenance records for merged papers.

For a selected project, calls db.find_conflicts() to identify differing source
metadata such as year and title. Differences are reported only; no fields are
modified. An empty result is not proof that cross-source deduplication failed.
"""

import argparse
from literature_agent.config import load_settings
from literature_agent.storage import database as db

parser = argparse.ArgumentParser()
parser.add_argument("--project", default="stage4-validation")
args = parser.parse_args()

conn = db.connect(load_settings().db_path)
try:
    project = db.require_project(conn, args.project)
    conflicts = []
    for paper in db.project_papers(conn, project["id"]):
        differences = db.find_conflicts(conn, paper["id"])
        if differences:
            conflicts.append((paper["id"], differences))
    for paper_id, differences in conflicts[:10]:
        print("Paper:", paper_id)
        print("Conflicts:", differences)
    print("Total papers with conflicts:", len(conflicts))
finally:
    conn.close()
