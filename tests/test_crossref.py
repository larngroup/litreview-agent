import httpx

from literature_agent.discovery.crossref import CrossrefSource, clean_jats, item_to_paper
from tests.conftest import mock_http

ITEM = {
    "DOI": "10.1145/ABC.123",
    "title": ["Human-in-the-loop machine learning: a survey"],
    "author": [{"given": "Ada", "family": "Lovelace"}, {"name": "HITL Consortium"}, {"given": ""}],
    "issued": {"date-parts": [[2021, 3, 4]]},
    "abstract": "<jats:title>Abstract</jats:title><jats:p>We review &amp; compare methods.</jats:p>",
    "subject": ["Computer Science"],
}


def test_clean_jats():
    assert clean_jats(ITEM["abstract"]) == "We review & compare methods."
    assert clean_jats(None) == ""


def test_item_to_paper():
    paper = item_to_paper(ITEM, "q")
    assert paper.source == "crossref" and paper.doi == "10.1145/abc.123"
    assert paper.source_id == "https://doi.org/10.1145/abc.123"
    assert paper.authors == ["Ada Lovelace", "HITL Consortium"]
    assert paper.year == 2021 and paper.keywords == ["Computer Science"]


def test_item_with_missing_fields():
    paper = item_to_paper({"issued": {"date-parts": [[None]]}}, "q")
    assert paper.title is None and paper.doi is None and paper.year is None and not paper.has_abstract


def test_search_uses_cursor_mailto_and_limit():
    def route(request):
        cursor = request.url.params["cursor"]
        if cursor == "*":
            items = [dict(ITEM, DOI=f"10.1/{i}") for i in range(100)]
            return httpx.Response(200, json={"message": {"items": items, "next-cursor": "NEXT"}})
        items = [dict(ITEM, DOI=f"10.1/{i}") for i in range(100, 200)]
        return httpx.Response(200, json={"message": {"items": items, "next-cursor": "NEXT2"}})

    http, seen = mock_http(route)
    papers = CrossrefSource(http, contact_email="me@example.org").search("hitl", limit=150)
    assert len(papers) == 150 and len(seen) == 2
    assert seen[0].url.params["mailto"] == "me@example.org"
    assert seen[0].url.params["rows"] == "100" and seen[1].url.params["cursor"] == "NEXT"
