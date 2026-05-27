import json
import re
import textwrap
import urllib.error
import urllib.request
from typing import Any

from app.settings import settings
from app.sql_guard import validate_sql

DEFAULT_SYSTEM_PROMPT = "你是 ChatBI 的后端连通性测试助手，请用简短中文回答。"
SQL_GENERATION_SYSTEM_PROMPT = (
    "你是 ChatBI 的 SQL 生成助手。你只能根据用户问题和给定数据资产元数据生成一条 MySQL SELECT。"
    "不要分析或总结真实业务数据，不要假设查询结果，不要输出解释。"
    "只返回 SQL 本身，禁止 INSERT、UPDATE、DELETE、DROP、ALTER、TRUNCATE、CREATE、CALL、OUTFILE。"
)


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


def build_sql_generation_prompt(
    question: str,
    catalog: dict[str, Any],
    sample_rows: list[dict[str, Any]] | None = None,
) -> str:
    return "\n".join(
        [
            "请为下面的业务问题生成一条只读 MySQL SELECT。",
            "安全约束：",
            "- 只允许 SELECT，且只允许一条语句。",
            "- 只能使用数据资产清单中的表和字段。",
            "- 如果用户问题包含明确实体值，WHERE 条件必须保留原始字面量，不要擅自简称、翻译或改写。",
            "- 示例：用户说“中东公司”时，条件值应使用 '中东公司'，不要改成 '中东'。",
            "- 不要接收、引用、分析或总结任何真实查询结果。",
            "- 不要输出 Markdown、解释、注释或多余文本。",
            "",
            f"用户问题：{question}",
            "",
            "数据资产清单：",
            json.dumps(compact_catalog_for_sql(catalog), ensure_ascii=False, indent=2),
        ]
    )


def compact_catalog_for_sql(catalog: dict[str, Any]) -> dict[str, Any]:
    assets = []
    for asset in catalog.get("assets", []):
        fields = []
        for field in asset.get("fields", []):
            fields.append(
                {
                    key: field.get(key)
                    for key in ("name", "cn_name", "chinese_name", "type", "aliases", "metric")
                    if field.get(key) not in (None, "", [])
                }
            )
        assets.append(
            {
                key: asset.get(key)
                for key in ("table", "name", "domain", "description", "aliases", "metric_paths")
                if asset.get(key) not in (None, "", [])
            }
            | {"fields": fields}
        )

    return {
        "assets": assets,
        "metric_definitions": catalog.get("metric_definitions", []),
    }


def extract_sql_from_completion(content: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    sql = fenced.group(1) if fenced else content
    sql = textwrap.dedent(sql).strip()
    sql = "\n".join(line.strip() for line in sql.splitlines() if line.strip())
    sql = re.sub(r"^\s*(SQL|sql)\s*[:：]\s*", "", sql)
    return sql.strip()


def generate_sql_from_question(
    question: str,
    catalog: dict[str, Any],
    temperature: float = 0.0,
) -> dict[str, Any]:
    prompt = build_sql_generation_prompt(question, catalog)
    completion = chat_completion(prompt, SQL_GENERATION_SYSTEM_PROMPT, temperature)
    sql = extract_sql_from_completion(completion.get("content", ""))
    validation = validate_sql(sql)
    return {
        "provider": completion.get("provider", "mock"),
        "model": completion.get("model", settings.deepseek_model),
        "sql": sql,
        "validation": validation,
        "finish_reason": completion.get("finish_reason"),
        "usage": completion.get("usage") or {},
    }
