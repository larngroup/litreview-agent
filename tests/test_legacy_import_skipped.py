"""Regression for Stage 3 legacy import, validated during Stage 5.

An explicitly skipped v4 record (no abstract) must not become a processing
failure. Real errors remain failed; valid boolean decisions remain ok.
Uses the existing pytest SQLite fixtures and makes no external API calls.
"""

import json

from literature_agent.storage import database as db
from literature_agent.storage.legacy_import import import_evaluated_json, import_papers_json


def test_legacy_import_distinguishes_skipped_from_failed(conn, project_id, tmp_path):
    records = [
        {"id": "https://openalex.org/W101", "title": "A relevant article without abstract", "abstract": ""},
        {"id": "https://openalex.org/W102", "title": "A paper whose model request failed", "abstract": "Real abstract"},
        {"id": "https://openalex.org/W103", "title": "A paper successfully classified", "abstract": "Real abstract"},
    ]
    papers_path = tmp_path / "papers.json"
    papers_path.write_text(json.dumps(records), encoding="utf-8")
    import_papers_json(conn, project_id, papers_path)

    evaluated = [
        {**records[0], "is_relevant": None, "status": "skipped_no_abstract", "reason": "Sem abstract disponível"},
        {**records[1], "is_relevant": None, "status": "failed", "reason": "Erro de processamento"},
        {**records[2], "is_relevant": True, "reason": "Matches the topic"},
    ]
    evaluated_path = tmp_path / "evaluated.json"
    evaluated_path.write_text(json.dumps(evaluated), encoding="utf-8")
    assert import_evaluated_json(conn, project_id, evaluated_path, "Human in the loop") == {
        "imported": 3, "unmatched": 0
    }

    rows = conn.execute(
        """SELECT s.status, s.decision, s.error
        FROM screenings s
        WHERE s.project_id = ?
        ORDER BY s.id""",
        (project_id,),
    ).fetchall()
    # Import preserves the evaluation records' order.
    assert [(r["status"], r["decision"]) for r in rows] == [
        ("skipped", "uncertain"),
        ("failed", None),
        ("ok", "include"),
    ]
    assert rows[0]["error"] is None
    assert rows[1]["error"] is not None
