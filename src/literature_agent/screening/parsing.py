"""Turn raw model text into validated Pydantic objects."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ResponseParseError(ValueError):
    """The model output was not valid JSON for the expected schema."""

    def __init__(self, message: str, raw_text: str | None):
        super().__init__(message)
        self.raw_text = raw_text


def extract_json_object(text: str | None) -> dict:
    """Return the first JSON object in `text` (plain, fenced, or after a preamble)."""
    if not isinstance(text, str) or not text.strip():
        raise ResponseParseError("The model returned an empty response.", text)
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ResponseParseError("No JSON object found in the model response.", text)


def parse_model_output(text: str | None, schema: type[T]) -> T:
    data = extract_json_object(text)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '(root)'}: {err['msg']}" for err in exc.errors()
        )
        raise ResponseParseError(f"JSON did not match the schema: {problems}", text) from exc
