import httpx
import pytest

from literature_agent import pipeline
from literature_agent.fulltext import store
from literature_agent.fulltext.download import DownloadError, download_pdf
from literature_agent.fulltext.locate import locate_open_access
from literature_agent.fulltext.pdf_text import ParseError, extract_pages
from literature_agent.storage import database as db
from tests.conftest import mock_http
from tests.pdf_helpers import make_pdf

PDF = make_pdf(["Objective: improve labelling with humans.", "Limitations: only 12 participants."])

OA_WORK = {"id": "https://openalex.org/W1",
           "open_access": {"is_oa": True, "oa_url": "https://repo.example.org/record/1"},
           "best_oa_location": {"is_oa": True, "pdf_url": "https://repo.example.org/1.pdf",
                                "landing_page_url": "https://repo.example.org/record/1",
                                "license": "cc-by", "version": "acceptedVersion"}}
CLOSED_WORK = {"id": "https://openalex.org/W2", "open_access": {"is_oa": False}, "best_oa_location": None}
UNPAYWALL = {"is_oa": True, "best_oa_location": {"url_for_pdf": "https://arxiv.example/2.pdf",
                                                  "url": "https://arxiv.example/abs/2", "license": None,
                                                  "version": "submittedVersion"}}


def router(request):
    url = str(request.url)
    if "api.openalex.org/works/doi:10.1/open" in url:
        return httpx.Response(200, json=OA_WORK)
    if "api.openalex.org/works/doi:10.1/closed" in url:
        return httpx.Response(200, json=CLOSED_WORK)
    if "api.unpaywall.org/v2/10.1/closed" in url:
        return httpx.Response(200, json=UNPAYWALL)
    return httpx.Response(404, json={"error": "not found"})


def test_locate_prefers_openalex_pdf():
    http, seen = mock_http(router)
    found = locate_open_access(http, doi="10.1/open", openalex_id=None, openalex_api_key="K", contact_email="me@x.org")
    assert found.locator == "openalex" and found.pdf_url.endswith("1.pdf") and found.license == "cc-by"
    assert len(seen) == 1 and seen[0].url.params["api_key"] == "K"


def test_locate_falls_back_to_unpaywall_and_handles_404():
    http, _ = mock_http(router)
    found = locate_open_access(http, doi="10.1/closed", openalex_id=None, openalex_api_key=None, contact_email="me@x.org")
    assert found.locator == "unpaywall" and found.version == "submittedVersion"
    assert locate_open_access(http, doi="10.1/unknown", openalex_id=None, openalex_api_key=None,
                              contact_email="me@x.org") is None
    # Without an e-mail address Unpaywall is not used.
    assert locate_open_access(http, doi="10.1/closed", openalex_id=None, openalex_api_key=None,
                              contact_email=None) is None


def client(responder):
    return httpx.Client(transport=httpx.MockTransport(responder))


def test_download_pdf_ok(tmp_path):
    result = download_pdf("https://x/1.pdf", tmp_path / "1.pdf", client=client(lambda r: httpx.Response(200, content=PDF)))
    assert result.size_bytes == len(PDF) and (tmp_path / "1.pdf").read_bytes() == PDF and len(result.sha256) == 64


@pytest.mark.parametrize("response, message", [
    (httpx.Response(200, content=b"<html>Please log in</html>"), "did not return a PDF"),
    (httpx.Response(403, content=b"Forbidden"), "HTTP 403"),
    (httpx.Response(200, content=b"%PDF-" + b"0" * 2000), "larger than"),
])
def test_download_rejections_leave_no_file(tmp_path, response, message):
    with pytest.raises(DownloadError, match=message):
        download_pdf("https://x/1.pdf", tmp_path / "1.pdf", client=client(lambda r: response), max_bytes=1000)
    assert list(tmp_path.iterdir()) == []


def test_extract_pages(tmp_path):
    path = tmp_path / "a.pdf"
    path.write_bytes(PDF)
    assert extract_pages(path) == ["Objective: improve labelling with humans.", "Limitations: only 12 participants."]
    broken = tmp_path / "b.pdf"
    broken.write_bytes(b"%PDF-1.4 garbage")
    with pytest.raises(ParseError):
        extract_pages(broken)


def test_pipeline_states_and_records_are_kept(conn, project_id, make_paper, tmp_path):
    ids = {}
    for name, doi in (("open", "10.1/open"), ("closed", "10.1/closed2"), ("noid", None)):
        paper = make_paper(source_id=None if name == "noid" else f"W-{name}", doi=doi,
                           title=f"A sufficiently long title for paper {name}")
        ids[name] = db.add_paper(conn, project_id, None, paper).paper_id
        db.add_review(conn, project_id, ids[name], "include")
    http, _ = mock_http(router)
    downloads = client(lambda r: httpx.Response(200, content=PDF))
    counts = pipeline.run_fulltext(conn, project_id, http=http, data_dir=tmp_path, download_client=downloads)
    assert counts == {"parsed": 1, "not_found": 1, "no_identifier": 1}
    pages = store.get_pages(conn, ids["open"])
    assert [p["page_number"] for p in pages] == [1, 2] and "12 participants" in pages[1]["text"]
    asset = store.get_asset(conn, ids["open"])
    assert asset["license"] == "cc-by" and asset["file_path"].endswith(f"{ids['open']}.pdf")
    assert len(db.project_papers(conn, project_id)) == 3          # nothing was deleted
    # Running again does not download again.
    again = pipeline.run_fulltext(conn, project_id, http=http, data_dir=tmp_path,
                                  download_client=client(lambda r: httpx.Response(500)))
    assert again["parsed"] == 1


def test_failed_download_can_be_retried(conn, project_id, make_paper, tmp_path):
    pid = db.add_paper(conn, project_id, None, make_paper(doi="10.1/open")).paper_id
    db.add_review(conn, project_id, pid, "include")
    http, _ = mock_http(router)
    first = pipeline.run_fulltext(conn, project_id, http=http, data_dir=tmp_path,
                                  download_client=client(lambda r: httpx.Response(503)))
    assert first == {"download_failed": 1} and "HTTP 503" in store.get_asset(conn, pid)["error"]
    retry = pipeline.run_fulltext(conn, project_id, http=http, data_dir=tmp_path, retry_failed=True,
                                  download_client=client(lambda r: httpx.Response(200, content=PDF)))
    assert retry == {"parsed": 1}


def test_schema_migration_from_version_1(tmp_path, make_paper):
    path = tmp_path / "old.db"
    conn = db.connect(path)
    pid = db.create_project(conn, "p", "t")
    db.add_paper(conn, pid, None, make_paper())
    with conn:
        conn.execute("DROP TABLE fulltext_pages")
        conn.execute("DROP TABLE fulltext_assets")
        conn.execute("UPDATE schema_info SET version = 1")
    conn.close()
    upgraded = db.connect(path)
    assert upgraded.execute("SELECT version FROM schema_info").fetchone()[0] == db.SCHEMA_VERSION
    assert upgraded.execute("SELECT COUNT(*) FROM fulltext_assets").fetchone()[0] == 0
    assert len(db.project_papers(upgraded, pid)) == 1
