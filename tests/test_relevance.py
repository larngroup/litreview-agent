import pytest

from literature_agent.screening.relevance import screen_paper, screen_papers
from tests.conftest import FakeProvider


def test_topic_is_passed_to_the_model(make_paper):
    provider = FakeProvider(['{"is_relevant": true, "reason": "fits"}'])
    result = screen_paper(make_paper(), "active learning", provider)
    assert "Research topic: active learning" in provider.calls[0]["user"]
    assert result["screening_status"] == "ok" and result["is_relevant"] is True
    assert result["screening_model"] == "fake-model" and result["screening_prompt_version"]


def test_missing_abstract_is_not_sent(make_paper):
    provider = FakeProvider([])
    result = screen_paper(make_paper(abstract=""), "t", provider)
    assert result["screening_status"] == "skipped_no_abstract" and provider.calls == []


def test_invalid_json_and_provider_errors_are_recorded(make_paper):
    provider = FakeProvider(["not json", RuntimeError("timeout")])
    bad, err = screen_papers([make_paper(), make_paper()], "t", provider)
    assert bad["screening_status"] == "failed" and bad["raw_response"] == "not json"
    assert err["screening_status"] == "failed" and "timeout" in err["screening_error"]


def test_empty_topic_rejected(make_paper):
    with pytest.raises(ValueError):
        screen_papers([make_paper()], "  ", FakeProvider([]))
