"""Summarize unique project additions for each scholarly source.

Adds the n_new values recorded in COMPLETED search_runs for a project.
These counts describe chronological contributions to this project, not the
number of papers exclusively indexed by a provider or a general coverage study.
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
    rows = conn.execute(
        """SELECT source, COUNT(*) AS completed_runs,
                  SUM(n_retrieved) AS retrieved, SUM(n_new) AS new_in_project
           FROM search_runs
           WHERE project_id = ? AND status = 'completed'
           GROUP BY source ORDER BY source""",
        (project["id"],),
    ).fetchall()
    for row in rows:
        print(dict(row))
    print("Project paper count:", len(db.project_papers(conn, project["id"])))
finally:
    conn.close()
