import pytest

from literature_agent import pipeline
from literature_agent.storage import database as db
from tests.conftest import FakeProvider


def test_run_search_stores_papers_and_run(conn, project_id, make_paper):
    papers = [make_paper(), make_paper(source_id="W2", doi="10.1/b", title="Another long paper title here")]
    summary = pipeline.run_search(conn, project_id, "hitl", 10, search_fn=lambda q, limit: papers)
    assert summary["retrieved"] == 2 and summary["new"] == 2
    again = pipeline.run_search(conn, project_id, "hitl", 10, search_fn=lambda q, limit: papers)
    assert again["new"] == 0 and again["duplicates"] == 2
    assert [r["status"] for r in db.list_search_runs(conn, project_id)] == ["completed", "completed"]


def test_failed_search_is_recorded(conn, project_id):
    def boom(q, limit):
        raise ConnectionError("network down")

    with pytest.raises(ConnectionError):
        pipeline.run_search(conn, project_id, "q", 5, search_fn=boom)
    run = db.list_search_runs(conn, project_id)[0]
    assert run["status"] == "failed" and "network down" in run["error"]


def test_screening_uses_project_topic_and_is_resumable(conn, project_id, make_paper):
    db.add_paper(conn, project_id, None, make_paper())
    db.add_paper(conn, project_id, None, make_paper(source_id="W2", doi="10.1/b", abstract=""))
    provider = FakeProvider(["garbage"])
    counts = pipeline.run_screening(conn, project_id, provider)
    assert counts == {"failed": 1, "skipped": 1}
    assert "human-in-the-loop machine learning" in provider.calls[0]["user"]

    assert pipeline.run_screening(conn, project_id, FakeProvider([])) == {}      # nothing new to do
    retry = FakeProvider(['{"is_relevant": true, "reason": "fits"}'])
    assert pipeline.run_screening(conn, project_id, retry, retry_failed=True) == {"ok": 1}
    decisions = {p["screening"]["decision"] for p in db.project_papers(conn, project_id)}
    assert decisions == {"include", "uncertain"}


def test_changing_topic_triggers_new_screening(conn, project_id, make_paper):
    db.add_paper(conn, project_id, None, make_paper())
    pipeline.run_screening(conn, project_id, FakeProvider(['{"is_relevant": true, "reason": "r"}']))
    counts = pipeline.run_screening(conn, project_id, FakeProvider(['{"is_relevant": false, "reason": "r"}']),
                                    topic="a different topic")
    assert counts == {"ok": 1}
