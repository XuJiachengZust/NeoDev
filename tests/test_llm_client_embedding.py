"""Unit tests for llm_client embedding/retry behavior."""

import httpx
import pytest


def test_get_llm_config_contains_embedding_fields(monkeypatch):
    from service.services.llm_client import get_llm_config

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OPENAI_BASE", "https://example.com/v1")
    monkeypatch.setenv("OPENAI_MODEL_CHAT", "chat-x")
    monkeypatch.setenv("OPENAI_MODEL_EMBEDDING", "embed-x")
    monkeypatch.setenv("OPENAI_REQUEST_MAX_RETRIES", "5")

    cfg = get_llm_config()
    assert cfg["api_key"] == "k"
    assert cfg["base_url"] == "https://example.com/v1"
    assert cfg["model_chat"] == "chat-x"
    assert cfg["model_embedding"] == "embed-x"
    assert cfg["max_retries"] == 5


def test_embedding_completion_returns_float_vector(monkeypatch):
    from service.services import llm_client

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(
        llm_client,
        "_post_json_with_retry",
        lambda **_: {"data": [{"embedding": [1, 2.5, "3.0"]}]},
    )

    vector = llm_client.embedding_completion("hello")
    assert vector == [1.0, 2.5, 3.0]


def test_embedding_completion_raises_on_invalid_shape(monkeypatch):
    from service.services import llm_client

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(
        llm_client,
        "_post_json_with_retry",
        lambda **_: {"data": [{"embedding": "not-a-list"}]},
    )

    with pytest.raises(RuntimeError, match="格式错误"):
        llm_client.embedding_completion("hello")


def test_post_json_with_retry_retries_on_transient_error():
    from service.services.llm_client import _post_json_with_retry

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class _Client:
        def __init__(self):
            self.calls = 0

        def post(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                request = httpx.Request("POST", "https://example.com")
                raise httpx.ConnectError("temporary", request=request)
            return _Resp()

    client = _Client()
    out = _post_json_with_retry(
        client=client,
        url="https://example.com",
        headers={},
        payload={"x": 1},
        retries=2,
    )
    assert out == {"ok": True}
    assert client.calls == 2
