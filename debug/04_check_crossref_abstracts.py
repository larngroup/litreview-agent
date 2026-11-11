"""Check whether Crossref actually returns abstracts in raw API metadata.

Compares the original JATS/XML abstract with its cleaned form for 10 search
results, using relevance sorting as in the corrected Stage 4 source. This
separates missing API metadata from a cleaning/screening problem. Network needed.
"""

import httpx
from literature_agent.config import load_settings
from literature_agent.discovery.crossref import CROSSREF_FIELDS, clean_jats

settings = load_settings()
params = {
    "query": "human-in-the-loop machine learning",
    "rows": 10,
    "cursor": "*",
    "sort": "score",
    "order": "desc",
    "select": ",".join(CROSSREF_FIELDS),
}
if settings.contact_email:
    params["mailto"] = settings.contact_email

response = httpx.get("https://api.crossref.org/works", params=params, timeout=30)
response.raise_for_status()
items = response.json()["message"].get("items", [])
for i, item in enumerate(items, 1):
    raw = item.get("abstract")
    cleaned = clean_jats(raw)
    print(f"\n{i}. {item.get('DOI')}")
    print("Title:", (item.get("title") or ["No title"])[0][:80])
    print("Abstract field exists:", "abstract" in item)
    print("Raw abstract length:", len(raw) if isinstance(raw, str) else 0)
    print("Cleaned abstract length:", len(cleaned))
    print("Preview:", cleaned[:150] or "(empty)")
