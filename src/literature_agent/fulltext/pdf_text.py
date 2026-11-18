"""Extract text page by page so that every later claim can cite a page number."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class ParseError(RuntimeError):
    pass


def extract_pages(path: Path) -> list[str]:
    """Return one string per page (page 1 = index 0). Raises ParseError."""
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ParseError("The PDF is encrypted.")
        pages = [" ".join((page.extract_text() or "").split()) for page in reader.pages]
    except ParseError:
        raise
    except (PdfReadError, OSError, ValueError, KeyError) as exc:
        raise ParseError(f"{type(exc).__name__}: {exc}") from exc
    if not any(pages):
        raise ParseError("No extractable text (the PDF may be scanned images; OCR is not supported yet).")
    return pages
