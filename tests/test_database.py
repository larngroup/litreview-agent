import pytest

from literature_agent.models import title_key
from literature_agent.storage import database as db


def test_title_key():
    assert title_key("Human-in-the-Loop  Machine Learning!") == title_key("human in the loop machine learning")
    assert title_key("Short") is None and title_key(None) is None


def test_create_project_and_duplicates(conn):
    pid = db.create_project(conn, "p", "topic", inclusion_criteria=["a"])
    assert db.get_project(conn, "p")["inclusion_criteria"] == ["a"]
    assert db.get_project(conn, pid)["name"] == "p"
    with pytest.raises(ValueError):
        db.create_project(conn, "p", "topic")
    with pytest.raises(ValueError):
        db.create_project(conn, "q", " ")


def test_same_doi_from_two_sources_is_merged_without_overwriting(conn, project_id, make_paper):
    first = db.add_paper(conn, project_id, None, make_paper(abstract="", year=2020))
    second = db.add_paper(conn, project_id, None, make_paper(
        source="crossref", source_id="10.1000/test", title="A different title for the same DOI",
        year=2021, abstract="Now we have an abstract."))
    assert first.new_paper and not second.new_paper and second.matched_by == "doi"
    paper = db.get_paper(conn, first.paper_id)
    assert paper["year"] == 2020                                   # not overwritten
    assert paper["title"] == "Human-in-the-loop machine learning"  # not overwritten
    assert paper["abstract"] == "Now we have an abstract."        # empty field filled
    assert len(db.get_paper_sources(conn, first.paper_id)) == 2    # provenance kept
    conflicts = db.find_conflicts(conn, first.paper_id)
    assert conflicts["year"] == [2020, 2021] and len(conflicts["title"]) == 2


def test_match_by_source_id_and_title(conn, project_id, make_paper):
    a = db.add_paper(conn, project_id, None, make_paper(doi=None))
    b = db.add_paper(conn, project_id, None, make_paper(doi=None, title="Changed title but same OpenAlex id"))
    assert b.matched_by == "source_id" and b.paper_id == a.paper_id
    c = db.add_paper(conn, project_id, None, make_paper(source="other", source_id="X", doi=None,
                                                         title="HUMAN in the loop: machine-learning"))
    assert c.matched_by == "title" and c.paper_id == a.paper_id


def test_title_match_rejected_when_years_or_dois_differ(conn, project_id, make_paper):
    a = db.add_paper(conn, project_id, None, make_paper(doi="10.1/a", year=2020))
    b = db.add_paper(conn, project_id, None, make_paper(source="x", source_id="1", doi="10.1/b", year=2020))
    c = db.add_paper(conn, project_id, None, make_paper(source="x", source_id="2", doi=None, year=2015))
    assert len({a.paper_id, b.paper_id, c.paper_id}) == 3


def test_paper_without_any_identifier_is_kept(conn, project_id, make_paper):
    result = db.add_paper(conn, project_id, None, make_paper(source_id=None, doi=None, title=None))
    assert result.new_paper and db.get_paper(conn, result.paper_id)["title"] is None


def test_new_in_project_flag(conn, project_id, make_paper):
    other = db.create_project(conn, "other", "t")
    first = db.add_paper(conn, project_id, None, make_paper())
    again = db.add_paper(conn, project_id, None, make_paper())
    elsewhere = db.add_paper(conn, other, None, make_paper())
    assert first.new_in_project and not again.new_in_project and elsewhere.new_in_project


def test_screening_and_review_are_separate(conn, project_id, make_paper):
    pid = db.add_paper(conn, project_id, None, make_paper()).paper_id
    db.add_screening(conn, project_id=project_id, paper_id=pid, status="ok", decision="include",
                     reason="model says yes", prompt_version="v", criteria_hash="h")
    row = db.project_papers(conn, project_id)[0]
    assert row["screening"]["decision"] == "include" and row["final_decision"] is None
    db.add_review(conn, project_id, pid, "exclude", note="wrong population")
    row = db.project_papers(conn, project_id)[0]
    assert row["final_decision"] == "exclude" and row["screening"]["decision"] == "include"
    with pytest.raises(ValueError):
        db.add_review(conn, project_id, pid, "maybe")


def test_latest_screening_per_criteria(conn, project_id, make_paper):
    pid = db.add_paper(conn, project_id, None, make_paper()).paper_id
    for status, crit in (("failed", "h1"), ("ok", "h1"), ("ok", "h2")):
        db.add_screening(conn, project_id=project_id, paper_id=pid, status=status,
                         decision="include" if status == "ok" else None, reason=None,
                         prompt_version="v", criteria_hash=crit)
    assert db.latest_screenings(conn, project_id, "h1")[pid]["status"] == "ok"
    assert db.latest_screenings(conn, project_id)[pid]["criteria_hash"] == "h2"


def test_search_runs_and_events(conn, project_id):
    run = db.start_search_run(conn, project_id, "openalex", "q", 10, {"x": 1})
    db.finish_search_run(conn, run, status="completed", n_retrieved=3, n_new=2, n_duplicates=1)
    db.log_event(conn, project_id, "info", "test", "hello", {"a": 1})
    assert db.list_search_runs(conn, project_id)[0]["n_new"] == 2
    assert db.list_events(conn, project_id)[0]["message"] == "hello"


def test_file_database_persists(tmp_path, make_paper):
    path = tmp_path / "sub" / "lit.db"
    conn = db.connect(path)
    pid = db.create_project(conn, "p", "t")
    db.add_paper(conn, pid, None, make_paper())
    conn.close()
    again = db.connect(path)
    assert len(db.project_papers(again, pid)) == 1
