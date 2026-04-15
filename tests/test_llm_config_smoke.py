"""Smoke test: after loading .env via main, LLM config is set and chat_completion works."""
import os
import sys
from pathlib import Path

# Load .env as main does
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))
try:
    from dotenv import load_dotenv
    load_dotenv(root / ".env")
except Exception:
    pass


def test_llm_config_has_api_key():
    from service.services.llm_client import get_llm_config
    cfg = get_llm_config()
    assert cfg.get("api_key"), "OPENAI_API_KEY should be set in .env"
    assert cfg.get("base_url")
    assert cfg.get("model_chat")
    assert cfg.get("model_embedding")


def test_llm_chat_completion_smoke():
    from service.services.llm_client import get_llm_config, chat_completion
    if not get_llm_config().get("api_key"):
        import pytest
        pytest.skip("OPENAI_API_KEY not set")
    r = chat_completion("Reply with exactly: OK")
    assert r
    assert "OK" in r.upper() or len(r.strip()) <= 10
