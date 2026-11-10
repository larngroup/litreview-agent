import httpx
import pytest

from literature_agent.discovery.openalex import (
    MAX_RECORDS, OpenAlexSource, reconstruct_abstract, work_to_paper,
)
from tests.conftest import mock_http


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
    assert paper.abstract == "Hello world"
    assert not work_to_paper({}, "q").has_abstract


def pages_router(pages):
    """Serve `pages` (lists of works) one after another using cursors c1, c2, ..."""
    def route(request):
        cursor = request.url.params["cursor"]
        index = 0 if cursor == "*" else int(cursor[1:])
        results = pages[index] if index < len(pages) else []
        next_cursor = f"c{index + 1}" if index + 1 < len(pages) else None
        return httpx.Response(200, json={"meta": {"next_cursor": next_cursor}, "results": results})
    return route


def works(start, stop):
    return [{"id": f"W{i}", "title": f"Paper {i}"} for i in range(start, stop)]


def test_search_follows_cursor_and_respects_limit():
    http, seen = mock_http(pages_router([works(0, 200), works(200, 400)]))
    papers = OpenAlexSource(http, api_key="KEY").search("hitl", limit=250)
    assert len(papers) == 250 and len(seen) == 2
    params = seen[0].url.params
    assert params["search"] == "hitl" and params["per_page"] == "200" and params["api_key"] == "KEY"
    assert "abstract_inverted_index" in params["select"]
    assert seen[1].url.params["cursor"] == "c1"


def test_search_stops_when_results_run_out():
    http, seen = mock_http(pages_router([works(0, 3)]))
    assert len(OpenAlexSource(http).search("q", limit=100)) == 3 and len(seen) == 1
    assert "api_key" not in seen[0].url.params


def test_search_skips_duplicates():
    http, _ = mock_http(pages_router([works(0, 5), works(3, 8)]))
    assert [p.source_id for p in OpenAlexSource(http).search("q", 100)] == [f"W{i}" for i in range(8)]


@pytest.mark.parametrize("limit", [0, -1, MAX_RECORDS + 1, "10", True])
def test_rejects_bad_limits(limit):
    http, _ = mock_http(lambda r: httpx.Response(500))
    with pytest.raises(ValueError):
        OpenAlexSource(http).search("q", limit=limit)
