"""A small HTTP helper shared by all scholarly sources: timeouts, retries, pacing."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import httpx

from .. import __version__

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}


class SourceError(RuntimeError):
    """A scholarly API could not be queried. The message is safe to show to users."""


class PoliteClient:
    """GET JSON with a timeout, bounded retries, Retry-After support and a minimum
    interval between requests (to stay inside each provider's published rate limits)."""

    def __init__(self, *, timeout: float = 30.0, max_retries: int = 4, backoff_seconds: float = 1.0,
                 min_interval_seconds: float = 0.0, contact_email: str | None = None,
                 client: httpx.Client | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        agent = f"literature-agent/{__version__}"
        if contact_email:
            agent += f" (mailto:{contact_email})"
        self._client = client or httpx.Client(timeout=timeout, headers={"User-Agent": agent},
                                              follow_redirects=True)
        if client is not None:
            self._client.headers.setdefault("User-Agent", agent)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.min_interval_seconds = min_interval_seconds
        self._sleep = sleep
        self._last_request = 0.0
        self.requests_made = 0

    def _wait_turn(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if self._last_request and elapsed < self.min_interval_seconds:
            self._sleep(self.min_interval_seconds - elapsed)

    def _retry_delay(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            header = response.headers.get("Retry-After", "")
            if header.strip().isdigit():
                return min(float(header), 60.0)
        return min(self.backoff_seconds * (2 ** attempt), 60.0)

    def get_json(self, url: str, params: dict) -> dict:
        safe_params = {k: v for k, v in params.items() if k not in {"api_key", "mailto"}}
        for attempt in range(self.max_retries + 1):
            self._wait_turn()
            response = None
            try:
                self._last_request = time.monotonic()
                self.requests_made += 1
                response = self._client.get(url, params=params, timeout=self.timeout)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise SourceError(f"{url} returned invalid JSON") from exc
                if response.status_code not in RETRY_STATUS:
                    raise SourceError(f"{url} returned HTTP {response.status_code}: {response.text[:300]}")
                problem = f"HTTP {response.status_code}"
            if attempt == self.max_retries:
                raise SourceError(f"{url} failed after {attempt + 1} attempts ({problem}); params={safe_params}")
            delay = self._retry_delay(attempt, response)
            log.warning("%s (%s); retrying in %.1fs", url, problem, delay)
            self._sleep(delay)
        raise AssertionError("unreachable")

    def close(self) -> None:
        self._client.close()
