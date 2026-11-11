"""Verify the Crossref access pool and rate-limit headers with CONTACT_EMAIL.

Uses the same free-text query endpoint as the application, prints status and
rate/concurrency headers, and does not display the email or any API credentials.
Requires network access; does not write to SQLite.
"""

import httpx
from literature_agent.config import load_settings

settings = load_settings()
if not settings.contact_email:
    raise SystemExit("CONTACT_EMAIL is not configured in .env")

response = httpx.get(
    "https://api.crossref.org/works",
    params={
        "query": "human-in-the-loop machine learning",
        "rows": 1,
        "mailto": settings.contact_email,
    },
    timeout=30,
)
print("HTTP status:", response.status_code)
response.raise_for_status()
for name, value in response.headers.items():
    if name.lower().startswith(("x-rate-limit", "x-concurrency", "x-api-pool")):
        print(f"{name}: {value}")
