import json
import urllib.error
import urllib.request
from typing import Any

from app.settings import settings

DEFAULT_SYSTEM_PROMPT = "你是 ChatBI 的后端连通性测试助手，请用简短中文回答。"


def llm_config_metadata() -> dict[str, Any]:
    provider = "deepseek" if settings.chatbi_llm_provider == "deepseek" else "mock"
    return {
        "provider": provider,
        "deepseek": {
            "enabled": provider == "deepseek",
            "base_url": settings.deepseek_api_base_url,
            "api_key_configured": bool(settings.deepseek_api_key.strip()),
            "model": settings.deepseek_model,
            "timeout": settings.deepseek_timeout,
        },
    }


def build_chat_payload(
    prompt: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    temperature: float = 0.1,
) -> dict[str, Any]:
    return {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "stream": False,
    }


def parse_chat_completion_response(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices") or []
    first_choice = choices[0] if choices else {}
    message = first_choice.get("message") or {}
    return {
        "provider": "deepseek",
        "id": data.get("id"),
        "model": data.get("model") or settings.deepseek_model,
        "content": message.get("content", ""),
        "finish_reason": first_choice.get("finish_reason"),
        "usage": data.get("usage") or {},
    }


def chat_completion(
    prompt: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    temperature: float = 0.1,
) -> dict[str, Any]:
    if settings.chatbi_llm_provider != "deepseek":
        return mock_completion(prompt)
    if not settings.deepseek_api_key.strip():
        raise RuntimeError("DEEPSEEK_API_KEY is required when CHATBI_LLM_PROVIDER=deepseek")

    payload = build_chat_payload(prompt, system_prompt, temperature)
    request = urllib.request.Request(
        f"{settings.deepseek_api_base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=settings.deepseek_timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek API request failed: {exc.reason}") from exc

    return parse_chat_completion_response(data)


def mock_completion(prompt: str) -> dict[str, Any]:
    return {
        "provider": "mock",
        "id": "mock-llm-test",
        "model": "mock",
        "content": f"mock LLM 已收到：{prompt}",
        "finish_reason": "stop",
        "usage": {},
    }
