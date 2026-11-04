"""Topic-based relevance screening (the notebook's evaluator, as a module)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Protocol

from pydantic import BaseModel, Field, StrictBool

from ..models import Paper, utc_now
from .parsing import ResponseParseError, parse_model_output

PROMPT_VERSION = "relevance-v1"

SYSTEM_PROMPT = (
    "You are screening scientific articles for a literature review. "
    "Judge relevance using ONLY the title, abstract and keywords provided. "
    "Do not use outside knowledge about the paper. Answer with a single JSON object."
)


class RelevanceAssessment(BaseModel):
    is_relevant: StrictBool
    reason: str = Field(min_length=1, max_length=1000)


class TextGenerator(Protocol):
    """Anything with this shape can screen papers (Groq now, Ollama in Stage 6)."""

    name: str
    model: str
    is_external: bool

    def generate(self, system: str, user: str, json_schema: dict | None = None): ...


def build_user_prompt(paper: Paper, topic: str) -> str:
    keywords = ", ".join(paper.keywords) or "(none)"
    return (
        f"Research topic: {topic}\n\n"
        f"Title: {paper.display_title}\n"
        f"Abstract: {paper.abstract}\n"
        f"Keywords: {keywords}\n\n"
        'Respond in exactly this JSON form: {"is_relevant": true or false, '
        '"reason": "one or two sentences explaining the decision"}'
    )


def screen_paper(paper: Paper, topic: str, provider: TextGenerator) -> dict:
    """Screen one paper and return a flat result dict (paper fields + screening fields)."""
    result = paper.model_dump(mode="json")
    result.update({
        "screening_topic": topic,
        "screening_provider": provider.name,
        "screening_model": provider.model,
        "screening_prompt_version": PROMPT_VERSION,
        "screened_at": utc_now().isoformat(),
        "screening_status": None,
        "is_relevant": None,
        "reason": None,
        "screening_error": None,
        "raw_response": None,
    })
    if not paper.has_abstract:
        result["screening_status"] = "skipped_no_abstract"
        result["reason"] = "No abstract available; needs manual or full-text screening."
        return result
    try:
        response = provider.generate(SYSTEM_PROMPT, build_user_prompt(paper, topic))
        result["raw_response"] = response.text
        assessment = parse_model_output(response.text, RelevanceAssessment)
    except ResponseParseError as exc:
        result.update(screening_status="failed", screening_error=str(exc))
        return result
    except Exception as exc:  # network / provider errors
        result.update(screening_status="failed", screening_error=f"{type(exc).__name__}: {exc}")
        return result
    result.update(screening_status="ok", is_relevant=assessment.is_relevant, reason=assessment.reason)
    return result


def screen_papers(
    papers: Iterable[Paper],
    topic: str,
    provider: TextGenerator,
    on_progress: Callable[[int, dict], None] | None = None,
) -> list[dict]:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("A research topic is required for screening.")
    results = []
    for index, paper in enumerate(papers, start=1):
        outcome = screen_paper(paper, topic, provider)
        results.append(outcome)
        if on_progress:
            on_progress(index, outcome)
    return results
