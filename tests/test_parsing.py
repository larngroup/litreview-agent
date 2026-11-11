import pytest

from literature_agent.screening.parsing import (
    ResponseParseError, extract_json_object, parse_model_output, strict_json_schema,
)
from literature_agent.screening.relevance import ScreeningOutput

VALID = '{"decision": "include", "reason": "ok", "matched_inclusion": [], "matched_exclusion": []}'


@pytest.mark.parametrize("text", [
    VALID,
    f"```json\n{VALID}\n```",
    f"Sure! {VALID} Hope this helps.",
    "{broken " + VALID,
])
def test_valid_responses(text):
    assert parse_model_output(text, ScreeningOutput).decision == "include"


@pytest.mark.parametrize("text", [
    None, "", "no json", "[1, 2]",
    '{"decision": "maybe", "reason": "r", "matched_inclusion": [], "matched_exclusion": []}',
    '{"decision": "include", "reason": "", "matched_inclusion": [], "matched_exclusion": []}',
    '{"decision": "include", "reason": "r"}',
])
def test_invalid_responses_raise_with_raw_text(text):
    with pytest.raises(ResponseParseError) as info:
        parse_model_output(text, ScreeningOutput)
    assert info.value.raw_text == text


def test_extract_first_object_only():
    assert extract_json_object('{"a": 1} {"b": 2}') == {"a": 1}


def test_strict_schema_shape():
    schema = strict_json_schema(ScreeningOutput)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"decision", "reason", "matched_inclusion", "matched_exclusion"}
    assert schema["properties"]["decision"]["enum"] == ["include", "exclude", "uncertain"]
