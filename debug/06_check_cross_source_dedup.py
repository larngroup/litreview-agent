"""Find papers with provenance from BOTH OpenAlex and Crossref.

Shows one merged papers row per publication and lists the distinct sources.
The final number is the TOTAL matching count, not just the displayed sample.
Optionally restrict to a project using --project. No data is modified.
"""

import argparse
from literature_agent.config import load_settings
from literature_agent.storage import database as db

parser = argparse.ArgumentParser()
parser.add_argument("--project", help="Optional project name; omit for global database")
args = parser.parse_args()

conn = db.connect(load_settings().db_path)
try:
    project_filter = ""
    params = []
    if args.project:
        project = db.require_project(conn, args.project)
        project_filter = "AND EXISTS (SELECT 1 FROM project_papers pp WHERE pp.paper_id = p.id AND pp.project_id = ?)"
        params.append(project["id"])
    rows = conn.execute(
        f"""SELECT p.id, p.title, GROUP_CONCAT(DISTINCT ps.source) AS sources
            FROM papers p
            JOIN paper_sources ps ON ps.paper_id = p.id
            WHERE ps.source IN ('openalex', 'crossref') {project_filter}
            GROUP BY p.id
            HAVING COUNT(DISTINCT ps.source) = 2
            ORDER BY p.id""",
        params,
    ).fetchall()
    for row in rows[:10]:
        print(dict(row))
    print("Articles found in both sources (total):", len(rows))
finally:
    conn.close()
