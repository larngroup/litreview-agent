"""Regression tests for sensitive data in HTTP errors."""

import httpx
import pytest

from literature_agent.discovery.http import PoliteClient, SourceError


@pytest.mark.parametrize("failure", [
    pytest.param(
        400,
        marks=pytest.mark.xfail(
            reason="Stage 10 TODO: redact sensitive HTTP response content",
            strict=True,
        ),
    ),
    429,
    pytest.param(
        "connection",
        marks=pytest.mark.xfail(
            reason="Stage 10 TODO: redact sensitive exception messages",
            strict=True,
        ),
    ),
])
def test_http_errors_do_not_expose_credentials(failure, caplog):
    api_key = "fake-test-api-key-123"
    email = "test@example.com"

    params = {
        "api_key": api_key,
        "email": email,
        "mailto": email,
        "search": "machine learning",
    }

    def handler(request):
        # Confirm that the real HTTP request still receives
        # the required parameters.
        assert request.url.params["api_key"] == api_key
        assert request.url.params["email"] == email
        assert request.url.params["mailto"] == email

        sensitive_message = f"api_key={api_key}, email={email}"

        if failure == "connection":
            raise httpx.ConnectError(
                sensitive_message,
                request=request,
            )

        return httpx.Response(
            failure,
            text=sensitive_message,
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        http = PoliteClient(
            client=client,
            max_retries=1,
            sleep=lambda _: None,
        )

        with pytest.raises(SourceError) as exc:
            http.get_json(
                "https://example.com/works",
                params,
            )

    message = str(exc.value)

    assert api_key not in message
    assert email not in message

    # Preserve useful diagnostic information.
    if failure == "connection":
        assert "ConnectError" in message
    else:
        assert f"HTTP {failure}" in message

    # Check application retry warnings, not third-party
    # HTTP debug logs (deferred until Stage 10).
    for record in caplog.records:
        if record.name == "literature_agent.discovery.http":
            assert api_key not in record.getMessage()
            assert email not in record.getMessage()