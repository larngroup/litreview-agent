import pytest

from literature_agent import pipeline
from literature_agent.storage import database as db
from tests.conftest import FakeProvider, FakeSource


def test_run_search_stores_papers_and_run(conn, project_id, make_paper):
    papers = [make_paper(), make_paper(source_id="W2", doi="10.1/b", title="Another long paper title here")]
    summary = pipeline.run_search(conn, project_id, "hitl", 10, FakeSource("openalex", papers))
    assert summary["retrieved"] == 2 and summary["new"] == 2
    again = pipeline.run_search(conn, project_id, "hitl", 10, FakeSource("openalex", papers))
    assert again["new"] == 0 and again["duplicates"] == 2
    assert [r["status"] for r in db.list_search_runs(conn, project_id)] == ["completed", "completed"]


def test_failed_search_is_recorded(conn, project_id):
    with pytest.raises(ConnectionError):
        pipeline.run_search(conn, project_id, "q", 5, FakeSource("openalex", error=ConnectionError("network down")))
    run = db.list_search_runs(conn, project_id)[0]
    assert run["status"] == "failed" and "network down" in run["error"]


def reply(decision):
    return ('{"decision": "%s", "reason": "r", "matched_inclusion": [], "matched_exclusion": []}' % decision)


def test_screening_is_resumable_and_retries_failures(conn, project_id, make_paper):
    db.update_project(conn, project_id, topic="human-in-the-loop machine learning",
                      research_question="Q?", inclusion_criteria=["empirical"], exclusion_criteria=[])
    db.add_paper(conn, project_id, None, make_paper())
    db.add_paper(conn, project_id, None, make_paper(source_id="W2", doi="10.1/b", abstract=""))
    provider = FakeProvider(["garbage", "garbage again"])
    counts = pipeline.run_screening(conn, project_id, provider)
    assert counts == {"failed": 1, "skipped": 1}
    assert "- empirical" in provider.calls[0]["user"]

    assert pipeline.run_screening(conn, project_id, FakeProvider([])) == {}      # nothing left to do
    retry = FakeProvider([reply("include")])
    assert pipeline.run_screening(conn, project_id, retry, retry_failed=True) == {"ok": 1}
    decisions = {p["screening"]["decision"] for p in db.project_papers(conn, project_id)}
    assert decisions == {"include", "uncertain"}
    events = [e["event"] for e in db.list_events(conn, project_id)]
    assert "screening_failed" in events and "screening_started" in events


def test_changed_criteria_trigger_new_screening(conn, project_id, make_paper):
    db.add_paper(conn, project_id, None, make_paper())
    pipeline.run_screening(conn, project_id, FakeProvider([reply("include")]))
    db.update_project(conn, project_id, topic="a different topic", research_question="",
                      inclusion_criteria=[], exclusion_criteria=[])
    assert pipeline.run_screening(conn, project_id, FakeProvider([reply("exclude")])) == {"ok": 1}


def test_settings_and_versions_are_recorded(conn, project_id, make_paper):
    pid = db.add_paper(conn, project_id, None, make_paper()).paper_id
    pipeline.run_screening(conn, project_id, FakeProvider([reply("include")]))
    screening = db.latest_screenings(conn, project_id)[pid]
    assert screening["model"] == "fake-model" and screening["prompt_version"] == "screening-v2"
    assert screening["settings"]["criteria"]["topic"] == "human-in-the-loop machine learning"


def test_max_papers(conn, project_id, make_paper):
    db.add_paper(conn, project_id, None, make_paper())
    db.add_paper(conn, project_id, None, make_paper(source_id="W2", doi="10.1/b"))
    assert pipeline.run_screening(conn, project_id, FakeProvider([reply("include")]), max_papers=1) == {"ok": 1}
