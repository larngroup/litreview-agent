from literature_agent import pipeline
from literature_agent.models import Paper
from literature_agent.storage import database as db
from tests.conftest import FakeSource


def test_openalex_and_crossref_records_merge(conn, project_id):
    openalex = FakeSource("openalex", [
        Paper(source="openalex", source_id="https://openalex.org/W1", doi="https://doi.org/10.1/AA",
              title="Human-in-the-loop machine learning", year=2021, abstract=""),
        Paper(source="openalex", source_id="https://openalex.org/W2", doi=None,
              title="Interactive labelling with crowd workers", year=2020, abstract="OpenAlex abstract"),
    ])
    crossref = FakeSource("crossref", [
        Paper(source="crossref", source_id="https://doi.org/10.1/aa", doi="10.1/aa",
              title="Human-in-the-loop Machine Learning", year=2021, abstract="Crossref abstract"),
        Paper(source="crossref", source_id="https://doi.org/10.9/zz", doi="10.9/zz",
              title="Interactive labelling with crowd workers", year=2020),
        Paper(source="crossref", source_id="https://doi.org/10.9/new", doi="10.9/new",
              title="A paper only Crossref knows about", year=2019),
    ])
    summaries = pipeline.run_multi_search(conn, project_id, "hitl", 10, [openalex, crossref])
    assert summaries[1]["matched_by"] == {"doi": 1, "title": 1} and summaries[1]["new"] == 1
    papers = db.project_papers(conn, project_id)
    assert len(papers) == 3
    merged = next(p for p in papers if p["doi"] == "10.1/aa")
    assert merged["abstract"] == "Crossref abstract"           # filled from the second source
    assert {s["source"] for s in db.get_paper_sources(conn, merged["id"])} == {"openalex", "crossref"}
    labelled = next(p for p in papers if p["title"].startswith("Interactive"))
    assert labelled["doi"] == "10.9/zz"                         # DOI learned from Crossref


def test_one_failing_source_does_not_stop_the_other(conn, project_id, make_paper):
    good = FakeSource("crossref", [make_paper(source="crossref")])
    bad = FakeSource("openalex", error=ConnectionError("down"))
    summaries = pipeline.run_multi_search(conn, project_id, "q", 5, [bad, good])
    assert "down" in summaries[0]["error"] and summaries[1]["new"] == 1
    assert [r["status"] for r in db.list_search_runs(conn, project_id)] == ["failed", "completed"]
