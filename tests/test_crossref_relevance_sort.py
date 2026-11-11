"""Regression test: Crossref cursor pagination must preserve relevance ordering.

Run before the fix (expected failure), then after adding sort=score/order=desc
(expected pass). All HTTP responses are simulated; no API calls are made.
"""

from literature_agent.discovery.crossref import CrossrefSource


def test_crossref_cursor_pagination_sorts_by_relevance():
    class FakeHTTP:
        def __init__(self):
            self.calls = []

        def get_json(self, url, params):
            self.calls.append(params.copy())
            if len(self.calls) == 1:
                return {
                    "message": {
                        "items": [{"DOI": "10.1234/first", "title": ["First paper"]}],
                        "next-cursor": "page-two",
                    }
                }
            return {
                "message": {
                    "items": [{"DOI": "10.1234/second", "title": ["Second paper"]}],
                    "next-cursor": None,
                }
            }

    http = FakeHTTP()
    papers = CrossrefSource(http).search("human-in-the-loop machine learning", limit=2)

    assert len(papers) == 2
    assert [call["cursor"] for call in http.calls] == ["*", "page-two"]
    assert all(call.get("sort") == "score" for call in http.calls)
    assert all(call.get("order") == "desc" for call in http.calls)
