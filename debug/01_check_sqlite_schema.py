"""Check whether the current SQLite database supports interrupted search runs.

Reads the search_runs table definition without changing the database. The
'interrupted' status was added after the Stage 3 Ctrl+C regression was found.
"""

from literature_agent.config import load_settings
from literature_agent.storage import database as db

conn = db.connect(load_settings().db_path)
try:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'search_runs' AND type = 'table'"
    ).fetchone()
    if row is None:
        raise RuntimeError("search_runs table not found")
    schema = row["sql"]
    print(schema)
    print("\nSupports interrupted:", "'interrupted'" in schema)
finally:
    conn.close()
