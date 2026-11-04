import pytest

from literature_agent.discovery.openalex import (
    MAX_RECORDS, reconstruct_abstract, search_openalex, work_to_paper,
)


@pytest.mark.parametrize("value", [None, {}, "text", 5, {"only": []}])
def test_reconstruct_abstract_empty_or_malformed(value):
    assert reconstruct_abstract(value) == ""


def test_reconstruct_abstract_order_gaps_and_bad_positions():
    index = {"The": [0, 3], "cat": [1], "sat": [2], "end": [6], "bad": ["x", -1, True]}
    assert reconstruct_abstract(index) == "The cat sat The end"


def test_work_to_paper_full_and_empty():
    work = {
        "id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/X", "title": " T ",
        "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Ada"}}, {"author": None}, None],
        "keywords": [{"display_name": "HITL"}, "junk"],
        "abstract_inverted_index": {"Hello": [0], "world": [1]},
    }
    paper = work_to_paper(work, "q")
    assert (paper.doi, paper.title, paper.authors, paper.keywords) == ("10.1/x", "T", ["Ada"], ["HITL"])
    assert paper.abstract == "Hello world" and paper.has_abstract
    empty = work_to_paper({}, "q")
    assert empty.title is None and empty.source_id is None and not empty.has_abstract


def fake_pager(pages):
    calls = {}

    def factory(query, per_page, n_max):
        calls.update(query=query, per_page=per_page, n_max=n_max)
        return iter(pages)

    return factory, calls


def works(start, stop):
    return [{"id": f"W{i}", "title": f"Paper {i}"} for i in range(start, stop)]


def test_search_respects_limit_above_one_page():
    # The original fetch_papers2 silently returned at most 100 records for limit=250.
    factory, calls = fake_pager([works(0, 200), works(200, 400)])
    papers = search_openalex("q", limit=250, pager_factory=factory)
    assert len(papers) == 250
    assert calls == {"query": "q", "per_page": 200, "n_max": 250}


def test_search_skips_duplicates():
    factory, _ = fake_pager([works(0, 5), works(3, 8)])
    papers = search_openalex("q", limit=100, pager_factory=factory)
    assert [p.source_id for p in papers] == [f"W{i}" for i in range(8)]


@pytest.mark.parametrize("limit", [0, -1, MAX_RECORDS + 1, "10", True])
def test_search_rejects_bad_limits(limit):
    with pytest.raises(ValueError):
        search_openalex("q", limit=limit, pager_factory=lambda *a: iter([]))


def test_search_rejects_empty_query():
    with pytest.raises(ValueError):
        search_openalex("   ", limit=5, pager_factory=lambda *a: iter([]))
