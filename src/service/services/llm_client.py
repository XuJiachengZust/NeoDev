"""LLM 调用：支持 chat/embeddings，含基础重试与响应校验。"""

import os
import time
from typing import Any

import httpx

_ENV_API_KEY = "OPENAI_API_KEY"
_ENV_BASE = "OPENAI_BASE"
_ENV_MODEL_CHAT = "OPENAI_MODEL_CHAT"
_ENV_MODEL_EMBEDDING = "OPENAI_MODEL_EMBEDDING"
_ENV_MAX_RETRIES = "OPENAI_REQUEST_MAX_RETRIES"

_DEFAULT_BASE = "https://api.openai.com/v1"
_DEFAULT_MODEL_CHAT = "gpt-4o-mini"
_DEFAULT_MODEL_EMBEDDING = "text-embedding-3-small"
_DEFAULT_MAX_RETRIES = 2


def _max_retries() -> int:
    raw = os.environ.get(_ENV_MAX_RETRIES, str(_DEFAULT_MAX_RETRIES)).strip()
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_MAX_RETRIES
    return max(0, value)


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or 500 <= status < 600
    return False


def _post_json_with_retry(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    retries: int,
) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise RuntimeError("LLM 返回格式错误：响应不是 JSON 对象")
            return data
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= retries or not _should_retry(exc):
                raise
            # 指数退避：0.5s, 1.0s, 2.0s...
            time.sleep(0.5 * (2**attempt))
    if last_exc:
        raise last_exc
    raise RuntimeError("LLM 请求失败")


def get_llm_config() -> dict:
    """从环境变量读取 LLM 配置（不包含 key 的明文，仅用于判断是否可用）。"""
    return {
        "api_key": os.environ.get(_ENV_API_KEY, "").strip(),
        "base_url": (os.environ.get(_ENV_BASE) or _DEFAULT_BASE).rstrip("/"),
        "model_chat": os.environ.get(_ENV_MODEL_CHAT) or _DEFAULT_MODEL_CHAT,
        "model_embedding": os.environ.get(_ENV_MODEL_EMBEDDING) or _DEFAULT_MODEL_EMBEDDING,
        "max_retries": _max_retries(),
    }


def chat_completion(prompt: str, system_prompt: str | None = None, max_tokens: int = 1024) -> str:
    """
    调用 OpenAI 兼容的 chat/completions 接口，返回助手回复文本。
    需设置环境变量 OPENAI_API_KEY；可选 OPENAI_BASE、OPENAI_MODEL_CHAT。
    """
    cfg = get_llm_config()
    if not cfg["api_key"]:
        raise ValueError("OPENAI_API_KEY 未设置，无法调用 LLM")

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    with httpx.Client(timeout=60.0) as client:
        data = _post_json_with_retry(
            client=client,
            url=f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            payload={
                "model": cfg["model_chat"],
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            retries=cfg["max_retries"],
        )
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 返回无 choices")
    content = (choices[0].get("message") or {}).get("content") or ""
    return content.strip()


def probe_chat(timeout: float = 10.0) -> tuple[bool, str]:
    """轻量探活：发一个最短 prompt 验证 chat 接口可用。返回 (ok, detail)。"""
    cfg = get_llm_config()
    if not cfg["api_key"]:
        return False, "OPENAI_API_KEY 未设置"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{cfg['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                json={"model": cfg["model_chat"], "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            )
            resp.raise_for_status()
            return True, f"chat OK (model={cfg['model_chat']})"
    except Exception as exc:  # noqa: BLE001
        return False, f"chat 不可用: {exc}"


def probe_embedding(timeout: float = 10.0) -> tuple[bool, str]:
    """轻量探活：发一个最短文本验证 embedding 接口可用。返回 (ok, detail)。"""
    cfg = get_llm_config()
    if not cfg["api_key"]:
        return False, "OPENAI_API_KEY 未设置"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{cfg['base_url']}/embeddings",
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                json={"model": cfg["model_embedding"], "input": "test"},
            )
            resp.raise_for_status()
            return True, f"embedding OK (model={cfg['model_embedding']})"
    except Exception as exc:  # noqa: BLE001
        return False, f"embedding 不可用: {exc}"


def embedding_completion(text: str) -> list[float]:
    """调用 OpenAI 兼容 embeddings 接口，返回向量。"""
    cfg = get_llm_config()
    if not cfg["api_key"]:
        raise ValueError("OPENAI_API_KEY 未设置，无法调用 embedding")
    payload = {"model": cfg["model_embedding"], "input": text}
    with httpx.Client(timeout=60.0) as client:
        data = _post_json_with_retry(
            client=client,
            url=f"{cfg['base_url']}/embeddings",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            payload=payload,
            retries=cfg["max_retries"],
        )
    items = data.get("data") or []
    if not items:
        raise RuntimeError("LLM embedding 返回无 data")
    embedding = items[0].get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("LLM embedding 返回格式错误")
    vector: list[float] = []
    for v in embedding:
        try:
            vector.append(float(v))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"LLM embedding 含非法数值: {v}") from exc
    return vector
