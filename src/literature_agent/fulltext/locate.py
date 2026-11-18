"""Find legal open-access copies via OpenAlex and Unpaywall.

We only ever use locations these services report as open access. We do not
scrape publisher pages, use shadow libraries or try to bypass paywalls.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from ..discovery.http import PoliteClient, SourceError


@dataclass(frozen=True)
class OALocation:
    locator: str                 # "openalex" or "unpaywall"
    pdf_url: str | None
    landing_url: str | None
    license: str | None
    version: str | None          # e.g. publishedVersion / acceptedVersion / submittedVersion


def _openalex_location(work: dict) -> OALocation | None:
    best = work.get("best_oa_location") or {}
    open_access = work.get("open_access") or {}
    if not (open_access.get("is_oa") or best.get("is_oa")):
        return None
    pdf = best.get("pdf_url")
    landing = best.get("landing_page_url") or open_access.get("oa_url")
    if not pdf and not landing:
        return None
    return OALocation("openalex", pdf, landing, best.get("license"), best.get("version"))


def locate_openalex(http: PoliteClient, *, doi: str | None, openalex_id: str | None,
                    api_key: str | None) -> OALocation | None:
    if doi:
        url = f"https://api.openalex.org/works/doi:{quote(doi, safe='/')}"
    elif openalex_id:
        url = "https://api.openalex.org/works/" + openalex_id.rsplit("/", 1)[-1]
    else:
        return None
    params = {"select": "id,open_access,best_oa_location"}
    if api_key:
        params["api_key"] = api_key
    try:
        return _openalex_location(http.get_json(url, params))
    except SourceError as exc:
        if exc.status_code == 404:
            return None
        raise


def locate_unpaywall(http: PoliteClient, *, doi: str, email: str) -> OALocation | None:
    try:
        data = http.get_json(f"https://api.unpaywall.org/v2/{quote(doi, safe='/')}", {"email": email})
    except SourceError as exc:
        if exc.status_code == 404:
            return None
        raise
    best = data.get("best_oa_location") or {}
    if not data.get("is_oa") or not best:
        return None
    pdf = best.get("url_for_pdf")
    landing = best.get("url_for_landing_page") or best.get("url")
    if not pdf and not landing:
        return None
    return OALocation("unpaywall", pdf, landing, best.get("license"), best.get("version"))


def locate_open_access(http: PoliteClient, *, doi: str | None, openalex_id: str | None,
                       openalex_api_key: str | None, contact_email: str | None) -> OALocation | None:
    """Prefer a location with a direct PDF link; OpenAlex first, then Unpaywall."""
    found = locate_openalex(http, doi=doi, openalex_id=openalex_id, api_key=openalex_api_key)
    if found and found.pdf_url:
        return found
    if doi and contact_email:   # Unpaywall requires an e-mail address
        other = locate_unpaywall(http, doi=doi, email=contact_email)
        if other and (other.pdf_url or not found):
            return other
    return found
