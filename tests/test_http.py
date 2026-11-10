import httpx
import pytest

from literature_agent.discovery.http import PoliteClient, SourceError


def client_for(responses, sleeps):
    replies = list(responses)

    def handler(request):
        item = replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return PoliteClient(client=httpx.Client(transport=httpx.MockTransport(handler)),
                        max_retries=2, backoff_seconds=1.0, sleep=sleeps.append)


def test_retries_429_with_retry_after_then_succeeds():
    sleeps = []
    http = client_for([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"ok": 1})], sleeps)
    assert http.get_json("https://x.test", {}) == {"ok": 1}
    assert sleeps == [7.0]


def test_retries_timeouts_with_backoff():
    sleeps = []
    http = client_for([httpx.ReadTimeout("slow"), httpx.Response(503), httpx.Response(200, json={})], sleeps)
    assert http.get_json("https://x.test", {}) == {}
    assert sleeps == [1.0, 2.0]


def test_gives_up_and_hides_secrets():
    http = client_for([httpx.Response(500)] * 3, [])
    with pytest.raises(SourceError) as info:
        http.get_json("https://x.test", {"api_key": "SECRET", "q": "a"})
    assert "SECRET" not in str(info.value) and "3 attempts" in str(info.value)


def test_client_errors_are_not_retried():
    http = client_for([httpx.Response(400, text="bad filter")], [])
    with pytest.raises(SourceError, match="HTTP 400: bad filter"):
        http.get_json("https://x.test", {})


def test_min_interval_between_requests():
    sleeps = []
    http = client_for([httpx.Response(200, json={}), httpx.Response(200, json={})], sleeps)
    http.min_interval_seconds = 5.0
    http.get_json("https://x.test", {})
    http.get_json("https://x.test", {})
    assert len(sleeps) == 1 and 4.0 < sleeps[0] <= 5.0
