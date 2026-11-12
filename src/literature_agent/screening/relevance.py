"""Criteria-based title/abstract screening.

IMPORTANT: this is *preliminary* screening on titles, abstracts and keywords.
An 'include' here means "worth reading in full", not "eligible for the review".
Final eligibility needs the full text and a human decision.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from ..models import Paper
from .parsing import ResponseParseError, parse_model_output, strict_json_schema

PROMPT_VERSION = "screening-v2"

Decision = Literal["include", "exclude", "uncertain"]

SYSTEM_PROMPT = """You assist with title/abstract screening for a systematic literature review.
Rules:
- Use ONLY the title, abstract and keywords provided. Do not use outside knowledge about the paper.
- Answer "include" only if the record plausibly satisfies ALL inclusion criteria and NO exclusion criterion.
- Answer "exclude" only if the record clearly fails an inclusion criterion or clearly meets an exclusion criterion.
- Answer "uncertain" when the information given is insufficient to decide. Prefer "uncertain" over guessing.
- Quote criteria exactly as written when listing which ones matched.
- Reply with a single JSON object and nothing else."""


class Criteria(BaseModel):
    topic: str
    research_question: str = ""
    inclusion: list[str] = Field(default_factory=list)
    exclusion: list[str] = Field(default_factory=list)

    @classmethod
    def from_project(cls, project: dict) -> "Criteria":
        return cls(topic=project["topic"], research_question=project.get("research_question") or "",
                   inclusion=project.get("inclusion_criteria") or [],
                   exclusion=project.get("exclusion_criteria") or [])

    def fingerprint(self, prompt_version: str = PROMPT_VERSION) -> str:
        """Same criteria + same prompt version => same hash => no re-screening needed."""
        payload = json.dumps({**self.model_dump(), "prompt_version": prompt_version}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ScreeningOutput(BaseModel):
    """The exact JSON shape the model must return."""

    decision: Decision
    reason: str = Field(min_length=1, max_length=1500)
    matched_inclusion: list[str]
    matched_exclusion: list[str]


SCREENING_SCHEMA = strict_json_schema(ScreeningOutput)


class TextGenerator(Protocol):
    name: str
    model: str
    is_external: bool

    def generate(self, system: str, user: str, json_schema: dict | None = None): ...


@dataclass
class ScreeningResult:
    status: Literal["ok", "failed", "skipped"]
    decision: Decision | None
    reason: str | None
    provider: str
    model: str
    details: dict = field(default_factory=dict)
    raw_response: str | None = None
    error: str | None = None


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none given)"


def build_user_prompt(paper: Paper, criteria: Criteria) -> str:
    return (
        f"Review topic: {criteria.topic}\n"
        f"Research question: {criteria.research_question or '(not specified)'}\n\n"
        f"Inclusion criteria:\n{_bullets(criteria.inclusion)}\n\n"
        f"Exclusion criteria:\n{_bullets(criteria.exclusion)}\n\n"
        "Record to screen:\n"
        f"Title: {paper.display_title}\n"
        f"Year: {paper.year or 'unknown'}\n"
        f"Abstract: {paper.abstract}\n"
        f"Keywords: {', '.join(paper.keywords) or '(none)'}\n\n"
        'Return JSON: {"decision": "include" | "exclude" | "uncertain", '
        '"reason": "one to three sentences", "matched_inclusion": [criteria met], '
        '"matched_exclusion": [exclusion criteria met]}'
    )


def screen_paper(paper: Paper, criteria: Criteria, provider: TextGenerator,
                 repair_attempts: int = 1) -> ScreeningResult:
    """Screen one record. Never raises: every failure becomes a 'failed' result."""
    base = dict(provider=provider.name, model=provider.model)
    if not paper.has_abstract:
        return ScreeningResult(
            status="skipped", decision="uncertain",
            reason="No abstract available; screen manually or after full-text retrieval.",
            details={"basis": "none"}, **base)

    user = build_user_prompt(paper, criteria)
    attempts: list[dict] = []
    for attempt in range(repair_attempts + 1):
        try:
            response = provider.generate(SYSTEM_PROMPT, user, json_schema=SCREENING_SCHEMA)
        except Exception as exc:  # network, auth, rate limit, provider bug
            attempts.append({"error": f"{type(exc).__name__}: {exc}"})
            return ScreeningResult(status="failed", decision=None, reason=None,
                                   details={"attempts": attempts},
                                   error=f"{type(exc).__name__}: {exc}", **base)
        try:
            output = parse_model_output(response.text, ScreeningOutput)
        except ResponseParseError as exc:
            attempts.append({"raw": response.text, "error": str(exc)})
            # One repair attempt: tell the model exactly what was wrong.
            user = (build_user_prompt(paper, criteria)
                    + f"\n\nYour previous reply was rejected: {exc}. Reply again with ONLY the JSON object.")
            continue
        unknown = [c for c in output.matched_inclusion if c not in criteria.inclusion] + \
                  [c for c in output.matched_exclusion if c not in criteria.exclusion]
        details = {"basis": "title+abstract+keywords",
                   "matched_inclusion": output.matched_inclusion,
                   "matched_exclusion": output.matched_exclusion,
                   "unrecognised_criteria": unknown,
                   "attempts": len(attempts) + 1,
                   "output_mode": getattr(response, "mode", None)}
        return ScreeningResult(status="ok", decision=output.decision, reason=output.reason,
                               details=details, raw_response=response.text, **base)
    return ScreeningResult(status="failed", decision=None, reason=None,
                           details={"attempts": attempts}, raw_response=attempts[-1].get("raw"),
                           error=attempts[-1]["error"], **base)
