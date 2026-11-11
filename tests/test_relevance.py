from literature_agent.screening.relevance import Criteria, screen_paper
from tests.conftest import FakeProvider

CRITERIA = Criteria(topic="human-in-the-loop ML", research_question="How do humans improve labelling?",
                    inclusion=["empirical study"], exclusion=["not peer reviewed"])


def reply(decision="include", inc=("empirical study",), exc=()):
    import json
    return json.dumps({"decision": decision, "reason": "because", "matched_inclusion": list(inc),
                       "matched_exclusion": list(exc)})


def test_prompt_contains_question_and_criteria(make_paper):
    provider = FakeProvider([reply()])
    result = screen_paper(make_paper(), CRITERIA, provider)
    user = provider.calls[0]["user"]
    assert "How do humans improve labelling?" in user and "- empirical study" in user and "- not peer reviewed" in user
    assert provider.calls[0]["json_schema"]["properties"]["decision"]["enum"] == ["include", "exclude", "uncertain"]
    assert result.status == "ok" and result.decision == "include"
    assert result.details["matched_inclusion"] == ["empirical study"] and result.details["attempts"] == 1


def test_uncertain_is_a_valid_outcome(make_paper):
    result = screen_paper(make_paper(), CRITERIA, FakeProvider([reply("uncertain", inc=())]))
    assert result.status == "ok" and result.decision == "uncertain"


def test_repair_attempt_after_invalid_output(make_paper):
    provider = FakeProvider(['{"decision": "maybe"}', reply("exclude", inc=(), exc=("not peer reviewed",))])
    result = screen_paper(make_paper(), CRITERIA, provider)
    assert result.status == "ok" and result.decision == "exclude" and result.details["attempts"] == 2
    assert "previous reply was rejected" in provider.calls[1]["user"]


def test_fails_after_repair_attempts(make_paper):
    result = screen_paper(make_paper(), CRITERIA, FakeProvider(["bad", "still bad"]))
    assert result.status == "failed" and result.decision is None and result.raw_response == "still bad"
    assert len(result.details["attempts"]) == 2


def test_provider_exception_is_recorded_not_raised(make_paper):
    result = screen_paper(make_paper(), CRITERIA, FakeProvider([TimeoutError("slow")]))
    assert result.status == "failed" and "slow" in result.error


def test_no_abstract_skipped_without_calling_model(make_paper):
    provider = FakeProvider([])
    result = screen_paper(make_paper(abstract=""), CRITERIA, provider)
    assert result.status == "skipped" and result.decision == "uncertain" and provider.calls == []


def test_unrecognised_criteria_are_flagged(make_paper):
    result = screen_paper(make_paper(), CRITERIA, FakeProvider([reply(inc=("something invented",))]))
    assert result.details["unrecognised_criteria"] == ["something invented"]


def test_fingerprint_changes_with_criteria():
    other = CRITERIA.model_copy(update={"inclusion": ["empirical study", "published after 2015"]})
    assert CRITERIA.fingerprint() != other.fingerprint()
    assert CRITERIA.fingerprint() == Criteria(**CRITERIA.model_dump()).fingerprint()
