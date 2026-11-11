""" 
check the import of old JSON files, the deduplication and the compatibility.
"""
import json

from literature_agent.storage import database as db
from literature_agent.storage.legacy_import import import_evaluated_json, import_papers_json

V4_PAPERS = [
    {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/A", "title": "Human in the loop learning systems",
     "year": 2023, "authors": ["A"], "keywords": ["k"], "has_abstract": True, "abstract": "Some text."},
    {"id": "https://openalex.org/W2", "doi": None, "title": "No Title Available", "year": None,
     "authors": [], "keywords": [], "has_abstract": False, "abstract": ""},
]
# Output of featcher_v1: no id, no doi, placeholder abstract
V4_TEST_PAPERS = [{"title": "Interactive machine learning with people", "abstract": "Abstract not available",
                   "keywords": []}]
V4_EVALUATED = [dict(V4_PAPERS[0], is_relevant=True, reason="About HITL"),
                dict(V4_PAPERS[1], is_relevant=None, reason="Erro de processamento")]


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_import_v4_files(conn, project_id, tmp_path):
    summary = import_papers_json(conn, project_id, write(tmp_path, "papers.json", V4_PAPERS))
    assert summary == {"run_id": summary["run_id"], "records": 2, "new": 2, "duplicates": 0}
    papers = db.project_papers(conn, project_id)
    assert papers[0]["doi"] == "10.1/a"
    assert papers[1]["title"] is None                     # placeholder removed
    run = db.list_search_runs(conn, project_id)[0]
    assert run["source"] == "legacy_json" and "file_modified_at" in run["parameters"]

    result = import_evaluated_json(conn, project_id, write(tmp_path, "eval.json", V4_EVALUATED),
                                   legacy_topic="Human in the loop")
    assert result == {"imported": 2, "unmatched": 0}
    screenings = db.latest_screenings(conn, project_id, "legacy")
    decisions = sorted((s["status"], s["decision"]) for s in screenings.values())
    assert decisions == [("failed", None), ("ok", "include")]


def test_import_is_repeatable_without_duplicates(conn, project_id, tmp_path):
    path = write(tmp_path, "papers.json", V4_PAPERS)
    import_papers_json(conn, project_id, path)
    second = import_papers_json(conn, project_id, path)
    assert second["new"] == 0 and second["duplicates"] == 2
    assert len(db.project_papers(conn, project_id)) == 2


def test_import_featcher_v1_output(conn, project_id, tmp_path):
    import_papers_json(conn, project_id, write(tmp_path, "t.json", V4_TEST_PAPERS), query="hitl")
    paper = db.project_papers(conn, project_id)[0]
    assert paper["abstract"] == "" and paper["has_abstract"] is False
