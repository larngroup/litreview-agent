import dataclasses

import pytest

from literature_agent.config import load_settings
from literature_agent.providers import LLMError, get_provider
from literature_agent.providers.ollama import is_local, list_ollama_models
from literature_agent.providers.openai_compatible import OpenAICompatibleProvider
from literature_agent.screening.relevance import SCREENING_SCHEMA
from tests.conftest import chat_reply


def provider_for(server, **overrides):
    options = dict(name="test", base_url=server.base_url, api_key="k", model="m",
                   max_retries=0, structured_mode="json_schema", strict_schema=True)
    options.update(overrides)
    return OpenAICompatibleProvider(**options)


def test_json_schema_mode_sends_schema(llm_server):
    llm_server.replies.append((200, chat_reply('{"ok": true}')))
    response = provider_for(llm_server).generate("s", "u", json_schema=SCREENING_SCHEMA)
    fmt = llm_server.requests[0]["body"]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["required"]
    assert response.mode == "json_schema" and response.text == '{"ok": true}'


def test_falls_back_when_schema_mode_is_rejected(llm_server):
    llm_server.replies += [(400, {"error": {"message": "response_format json_schema not supported"}}),
                           (200, chat_reply("{}"))]
    response = provider_for(llm_server).generate("s", "u", json_schema=SCREENING_SCHEMA)
    assert response.mode == "json_object"
    assert llm_server.requests[1]["body"]["response_format"] == {"type": "json_object"}


def test_falls_back_to_plain_text(llm_server):
    llm_server.replies += [(400, {"error": {"message": "no"}}), (400, {"error": {"message": "no"}}),
                           (200, chat_reply("text"))]
    response = provider_for(llm_server).generate("s", "u", json_schema=SCREENING_SCHEMA)
    assert response.mode == "none" and "response_format" not in llm_server.requests[2]["body"]


def test_all_modes_rejected_is_an_llm_error(llm_server):
    llm_server.replies += [(400, {"error": {"message": "bad"}})] * 3
    with pytest.raises(LLMError, match="every structured-output mode"):
        provider_for(llm_server).generate("s", "u", json_schema=SCREENING_SCHEMA)


def test_without_schema_json_schema_mode_uses_json_object(llm_server):
    llm_server.replies.append((200, chat_reply("{}")))
    assert provider_for(llm_server).generate("s", "u").mode == "json_object"


@pytest.mark.parametrize("status, message", [(401, "authentication"), (404, "not found")])
def test_clear_errors(llm_server, status, message):
    llm_server.replies.append((status, {"error": {"message": "x"}}))
    with pytest.raises(LLMError, match=message):
        provider_for(llm_server).generate("s", "u")


def test_connection_error_is_clear(monkeypatch):
    import httpx
    import openai

    provider = OpenAICompatibleProvider(
        name="t",
        base_url="http://127.0.0.1:9/v1",
        api_key="k",
        model="m",
        max_retries=0,
        timeout=2,
    )

    def fake_create(**kwargs):
        raise openai.APIConnectionError(
            request=httpx.Request(
                "POST",
                "http://127.0.0.1:9/v1/chat/completions"
            )
        )

    monkeypatch.setattr(
        provider._client.chat.completions,
        "create",
        fake_create
    )

    with pytest.raises(LLMError, match="cannot connect"):
        provider.generate("s", "u")


@pytest.fixture
def settings(monkeypatch, tmp_path):
    for name in ("GROQ_API_KEY", "LLM_PROVIDER", "LLM_STRUCTURED_MODE", "GROQ_MODEL", "OLLAMA_MODEL"):
        monkeypatch.delenv(name, raising=False)
    return load_settings(env_file=None)


def test_factory_groq(settings):
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        get_provider(settings, "groq")
    groq = get_provider(dataclasses.replace(settings, groq_api_key="k"), "groq")
    assert groq.is_external and groq.structured_mode == "json_schema" and groq.strict_schema
    other = get_provider(dataclasses.replace(settings, groq_api_key="k"), "groq", model="qwen/qwen3.6-27b")
    assert other.structured_mode == "json_object" and not other.strict_schema


def test_factory_ollama_checks_installed_models(settings, llm_server):
    local = dataclasses.replace(settings, ollama_base_url=llm_server.base_url, ollama_model="llama3.1:8b")
    llm_server.replies.append((200, {"models": [{"name": "llama3.1:8b"}, {"name": "qwen3:latest"}]}))
    provider = get_provider(local, "ollama")
    assert provider.name == "ollama" and not provider.is_external
    assert llm_server.requests[0]["path"] == "/api/tags"
    llm_server.replies.append((200, {"models": [{"name": "qwen3:latest"}]}))
    assert get_provider(local, "ollama", model="qwen3").model == "qwen3"
    llm_server.replies.append((200, {"models": []}))
    with pytest.raises(LLMError, match="ollama pull llama3.1:8b"):
        get_provider(local, "ollama")


def test_ollama_not_running():
    with pytest.raises(LLMError, match="ollama serve"):
        list_ollama_models("http://127.0.0.1:9/v1", timeout=1)


def test_remote_ollama_counts_as_external():
    assert is_local("http://localhost:11434/v1") and not is_local("https://gpu.example.org/v1")


def test_unknown_provider(settings):
    with pytest.raises(ValueError):
        get_provider(settings, "magic")


def test_screening_end_to_end_through_real_http(llm_server, make_paper):
    from literature_agent.screening.relevance import Criteria, screen_paper
    llm_server.replies.append((200, chat_reply(
        '{"decision": "include", "reason": "r", "matched_inclusion": [], "matched_exclusion": []}')))
    result = screen_paper(make_paper(), Criteria(topic="t"), provider_for(llm_server))
    assert result.status == "ok" and result.details["output_mode"] == "json_schema"
