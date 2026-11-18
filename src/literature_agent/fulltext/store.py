"""Database access for full-text assets and pages."""

from __future__ import annotations

from ..models import utc_now

ASSET_FIELDS = ("access_status", "locator", "pdf_url", "landing_url", "license", "oa_version",
                "download_status", "file_path", "sha256", "size_bytes", "parse_status", "n_pages", "error")


def get_asset(conn, paper_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM fulltext_assets WHERE paper_id = ?", (paper_id,)).fetchone()
    return dict(row) if row else None


def save_asset(conn, paper_id: int, **fields) -> int:
    """Create or update the single asset row of a paper."""
    unknown = set(fields) - set(ASSET_FIELDS)
    if unknown:
        raise ValueError(f"Unknown asset fields: {unknown}")
    now = utc_now().isoformat()
    with conn:
        existing = get_asset(conn, paper_id)
        if existing is None:
            columns = ["paper_id", *fields, "updated_at"]
            conn.execute(f"INSERT INTO fulltext_assets ({', '.join(columns)}) VALUES "
                         f"({', '.join('?' for _ in columns)})", (paper_id, *fields.values(), now))
        elif fields:
            assignments = ", ".join(f"{name} = ?" for name in fields)
            conn.execute(f"UPDATE fulltext_assets SET {assignments}, updated_at = ? WHERE paper_id = ?",
                         (*fields.values(), now, paper_id))
    return get_asset(conn, paper_id)["id"]


def save_pages(conn, asset_id: int, pages: list[str]) -> None:
    with conn:
        conn.execute("DELETE FROM fulltext_pages WHERE asset_id = ?", (asset_id,))
        conn.executemany("INSERT INTO fulltext_pages (asset_id, page_number, text) VALUES (?, ?, ?)",
                         [(asset_id, number, text) for number, text in enumerate(pages, start=1)])


def get_pages(conn, paper_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT fp.page_number, fp.text FROM fulltext_pages fp JOIN fulltext_assets fa ON fa.id = fp.asset_id "
        "WHERE fa.paper_id = ? ORDER BY fp.page_number", (paper_id,))
    return [dict(r) for r in rows]


def project_assets(conn, project_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT fa.*, p.title, p.doi FROM fulltext_assets fa JOIN project_papers pp ON pp.paper_id = fa.paper_id "
        "JOIN papers p ON p.id = fa.paper_id WHERE pp.project_id = ? ORDER BY fa.paper_id", (project_id,))
    return [dict(r) for r in rows]
