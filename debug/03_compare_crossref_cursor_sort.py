"""Compare Crossref search results with and without cursor relevance sorting.

Reproduces the Stage 4 discovery bug: cursor='*' without sort=score returned
mostly unrelated articles for our test query. Three requests show DOI, abstract
presence and title so their actual ranking can be compared. Network required.
"""

import httpx
from literature_agent.config import load_settings
from literature_agent.discovery.crossref import CROSSREF_FIELDS

settings = load_settings()
base = {
    "query": "human-in-the-loop machine learning",
    "rows": 10,
    "select": ",".join(CROSSREF_FIELDS),
}
if settings.contact_email:
    base["mailto"] = settings.contact_email

with httpx.Client(timeout=30) as client:
    for label, extra in [
        ("WITHOUT CURSOR", {}),
        ("WITH CURSOR", {"cursor": "*"}),
        ("CURSOR + RELEVANCE SORT", {"cursor": "*", "sort": "score", "order": "desc"}),
    ]:
        response = client.get("https://api.crossref.org/works", params={**base, **extra})
        response.raise_for_status()
        print(f"\n=== {label} ===")
        for i, item in enumerate(response.json()["message"].get("items", []), 1):
            title = (item.get("title") or [""])[0]
            print(f"{i}. {item.get('DOI')} | abstract={bool(item.get('abstract'))} | {title[:70]}")
