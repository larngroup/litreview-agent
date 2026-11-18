"""Download a PDF from an open-access URL, with size and type checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import httpx

from .. import __version__

MAX_BYTES = 50 * 1024 * 1024


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadedFile:
    path: Path
    sha256: str
    size_bytes: int


def download_pdf(url: str, destination: Path, *, client: httpx.Client | None = None,
                 timeout: float = 60.0, contact_email: str | None = None,
                 max_bytes: int = MAX_BYTES) -> DownloadedFile:
    agent = f"literature-agent/{__version__}" + (f" (mailto:{contact_email})" if contact_email else "")
    own_client = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": agent})
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".part")
    digest, size = hashlib.sha256(), 0
    try:
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise DownloadError(f"HTTP {response.status_code} from {url}")
            with partial.open("wb") as handle:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise DownloadError(f"File larger than {max_bytes // (1024 * 1024)} MB")
                    digest.update(chunk)
                    handle.write(chunk)
        with partial.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                # Often an HTML landing page or a login/cookie wall: we do not try to get around it.
                raise DownloadError("The URL did not return a PDF (probably an HTML page).")
        partial.replace(destination)
        return DownloadedFile(destination, digest.hexdigest(), size)
    except httpx.HTTPError as exc:
        raise DownloadError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        if partial.exists():
            partial.unlink()
        if own_client:
            client.close()
