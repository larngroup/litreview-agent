"""Exports built ONLY from stored records. Nothing here invents or completes metadata:
a field that the sources did not provide is left out (BibTeX) or empty (CSV)."""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata

CSV_COLUMNS = ["paper_id", "title", "year", "authors", "doi", "doi_url", "has_abstract",
               "model_decision", "model_reason", "model", "prompt_version",
               "human_decision", "human_note", "decision_basis"]


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _bibtex_escape(text: str) -> str:
    return re.sub(r"([&%$#_{}])", r"\\\1", text)


def citation_key(paper: dict, used: set[str]) -> str:
    first_author = paper["authors"][0].split()[-1] if paper.get("authors") else "anon"
    first_word = next((w for w in re.findall(r"[A-Za-z]+", _ascii(paper.get("title") or "")) if len(w) > 3), "untitled")
    base = re.sub(r"[^a-z0-9]", "", f"{_ascii(first_author)}{paper.get('year') or 'nd'}{first_word}".lower())
    key, suffix = base, ord("a")
    while key in used:
        key = f"{base}{chr(suffix)}"
        suffix += 1
    used.add(key)
    return key


def to_bibtex(papers: list[dict]) -> str:
    used: set[str] = set()
    entries = []
    for paper in papers:
        fields = []
        if paper.get("title"):
            fields.append(f"  title = {{{_bibtex_escape(paper['title'])}}}")
        if paper.get("authors"):
            fields.append(f"  author = {{{_bibtex_escape(' and '.join(paper['authors']))}}}")
        if paper.get("year"):
            fields.append(f"  year = {{{paper['year']}}}")
        if paper.get("doi"):
            fields.append(f"  doi = {{{paper['doi']}}}")
            fields.append(f"  url = {{https://doi.org/{paper['doi']}}}")
        fields.append(f"  note = {{literature-agent paper id {paper['id']}}}")
        entries.append(f"@misc{{{citation_key(paper, used)},\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(entries) + ("\n" if entries else "")


def _csv_row(paper: dict) -> dict:
    screening = paper.get("screening") or {}
    review = paper.get("review") or {}
    return {
        "paper_id": paper["id"], "title": paper.get("title") or "", "year": paper.get("year") or "",
        "authors": "; ".join(paper.get("authors") or []), "doi": paper.get("doi") or "",
        "doi_url": f"https://doi.org/{paper['doi']}" if paper.get("doi") else "",
        "has_abstract": paper.get("has_abstract", False),
        "model_decision": screening.get("decision") or "", "model_reason": screening.get("reason") or "",
        "model": screening.get("model") or "", "prompt_version": screening.get("prompt_version") or "",
        "human_decision": review.get("decision") or "", "human_note": review.get("note") or "",
        "decision_basis": "title/abstract screening only",
    }


def to_csv(papers: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for paper in papers:
        writer.writerow(_csv_row(paper))
    return buffer.getvalue()


def search_history_csv(runs: list[dict]) -> str:
    columns = ["id", "source", "query", "requested_limit", "status", "started_at", "finished_at",
               "n_retrieved", "n_new", "n_duplicates", "error"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(runs)
    return buffer.getvalue()


def to_json(papers: list[dict], project: dict, runs: list[dict]) -> str:
    return json.dumps({"project": project, "search_runs": runs, "papers": papers},
                      indent=2, ensure_ascii=False, default=str)


def select_papers(papers: list[dict], subset: str) -> list[dict]:
    """subset: 'human_include' | 'model_include_unreviewed' | 'all'."""
    if subset == "human_include":
        return [p for p in papers if p["final_decision"] == "include"]
    if subset == "model_include_unreviewed":
        return [p for p in papers if p["final_decision"] is None
                and (p.get("screening") or {}).get("decision") == "include"]
    if subset == "all":
        return list(papers)
    raise ValueError(f"Unknown subset {subset!r}")
