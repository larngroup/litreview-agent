import pytest

from literature_agent.screening.parsing import ResponseParseError, extract_json_object, parse_model_output
from literature_agent.screening.relevance import RelevanceAssessment


@pytest.mark.parametrize("text", [
    '{"is_relevant": true, "reason": "ok"}',
    '```json\n{"is_relevant": true, "reason": "ok"}\n```',
    'Sure! {"is_relevant": true, "reason": "ok"} Hope this helps.',
    '{broken {"is_relevant": true, "reason": "ok"}',
])
def test_valid_responses(text):
    assert parse_model_output(text, RelevanceAssessment).is_relevant is True


@pytest.mark.parametrize("text", [
    None, "", "no json", "[1, 2]",
    '{"is_relevant": "yes", "reason": "r"}',
    '{"is_relevant": true}',
    '{"is_relevant": true, "reason": ""}',
])
def test_invalid_responses_raise_with_raw_text(text):
    with pytest.raises(ResponseParseError) as info:
        parse_model_output(text, RelevanceAssessment)
    assert info.value.raw_text == text


def test_extract_first_object_only():
    assert extract_json_object('{"a": 1} {"b": 2}') == {"a": 1}
