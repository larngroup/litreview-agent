"""Compare model suggestions with human decisions (a manually reviewed sample).

Run this on 50-100 human-reviewed records BEFORE trusting the model on a new
topic. For screening, the most important number is recall of 'include':
a paper the model wrongly excludes may never be read.
"""

from __future__ import annotations

from collections import Counter

LABELS = ("include", "exclude", "uncertain")


def agreement_report(papers: list[dict]) -> dict:
    """`papers` as returned by storage.database.project_papers()."""
    pairs = [(p["review"]["decision"], p["screening"]["decision"])
             for p in papers
             if p.get("review") and p.get("screening") and p["screening"]["status"] == "ok"]
    matrix = Counter(pairs)
    total = len(pairs)
    agreed = sum(n for (human, model), n in matrix.items() if human == model)
    human_includes = sum(n for (human, _), n in matrix.items() if human == "include")
    model_hits = matrix[("include", "include")]
    missed = matrix[("include", "exclude")]
    return {
        "compared": total,
        "agreement": round(agreed / total, 3) if total else None,
        "include_recall": round(model_hits / human_includes, 3) if human_includes else None,
        "includes_wrongly_excluded": missed,
        "matrix": {f"human={h}/model={m}": matrix[(h, m)] for h in LABELS for m in LABELS if matrix[(h, m)]},
    }
