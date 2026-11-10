"""Shared test helpers. No test in this suite touches the network."""

from __future__ import annotations

import pytest

from literature_agent.models import Paper


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeProvider:
    """Returns canned responses in order and records every prompt it receives."""

    name = "fake"
    model = "fake-model"
    is_external = False

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, system, user, json_schema=None):
        self.calls.append({"system": system, "user": user, "json_schema": json_schema})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)


@pytest.fixture
def make_paper():
    def _make(**overrides) -> Paper:
        data = {
            "source": "openalex",
            "source_id": "https://openalex.org/W1",
            "doi": "10.1000/test",
            "title": "Human-in-the-loop machine learning",
            "year": 2024,
            "authors": ["Ada Lovelace"],
            "keywords": ["human-in-the-loop"],
            "abstract": "We study interactive labelling with humans in the loop.",
            "query": "human in the loop",
        }
        data.update(overrides)
        return Paper(**data)

    return _make


# ---------------------------------------------------------------------------
# A tiny local HTTP server that imitates an OpenAI-compatible /chat/completions
# endpoint. Using a real socket keeps the tests independent of the openai
# library's internal HTTP client, which differs between openai versions.
# ---------------------------------------------------------------------------
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def chat_reply(content: str) -> dict:
    return {
        "id": "test", "object": "chat.completion", "created": 0, "model": "test-model",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
    }


class FakeLLMServer:
    """`replies` is a list of (status_code, json_body) returned in order."""

    def __init__(self):
        self.replies: list[tuple[int, dict]] = []
        self.requests: list[dict] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 (name required by BaseHTTPRequestHandler)
                length = int(self.headers.get("Content-Length", 0))
                server.requests.append({"path": self.path, "body": json.loads(self.rfile.read(length))})
                status, body = server.replies.pop(0) if server.replies else (500, {"error": "no reply"})
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):  # noqa: N802
                server.requests.append({"path": self.path, "body": None})
                status, body = server.replies.pop(0) if server.replies else (404, {})
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):  # keep test output quiet
                pass

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._httpd.server_port}/v1"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture
def llm_server():
    server = FakeLLMServer()
    yield server
    server.close()


@pytest.fixture
def conn():
    """A fresh in-memory database for each test."""
    from literature_agent.storage import database as db

    connection = db.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def project_id(conn):
    from literature_agent.storage import database as db

    return db.create_project(conn, "test", "human-in-the-loop machine learning")


class FakeSource:
    """A search source that returns fixed papers (or raises an exception)."""

    def __init__(self, name, papers=None, error=None):
        self.name = name
        self.papers = papers or []
        self.error = error
        self.calls = []

    def search(self, query, limit=100):
        self.calls.append((query, limit))
        if self.error:
            raise self.error
        return self.papers[:limit]


def mock_http(routes):
    """PoliteClient whose requests are answered by `routes(request) -> httpx.Response`."""
    import httpx

    from literature_agent.discovery.http import PoliteClient

    seen = []

    def handler(request):
        seen.append(request)
        return routes(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteClient(client=client, max_retries=2, sleep=lambda s: None), seen
