import pytest

from literature_agent.providers.groq import GroqProvider, LLMError
from tests.conftest import chat_reply


def test_generate_sends_json_mode_and_returns_text(llm_server):
    llm_server.replies.append((200, chat_reply('{"is_relevant": true, "reason": "r"}')))
    provider = GroqProvider(api_key="k", model="m", base_url=llm_server.base_url, max_retries=0)
    response = provider.generate("sys", "user")
    body = llm_server.requests[0]["body"]
    assert llm_server.requests[0]["path"] == "/v1/chat/completions"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert response.text.startswith("{") and response.model == "m"


def test_http_error_becomes_llm_error(llm_server):
    llm_server.replies.append((401, {"error": {"message": "Invalid API Key"}}))
    provider = GroqProvider(api_key="k", model="m", base_url=llm_server.base_url, max_retries=0)
    with pytest.raises(LLMError, match="Invalid API Key"):
        provider.generate("s", "u")


def test_missing_key_is_a_clear_error():
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        GroqProvider(api_key="", model="m", base_url="https://x")
