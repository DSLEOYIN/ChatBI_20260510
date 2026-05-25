import asyncio
import http.client
import json
from typing import Any
from urllib.parse import urlsplit

from app.mock.catalog import DIFY_DATASET_ALIASES, DIFY_DATASETS, MOCK_DIFY_RECORDS
from app.models.schemas import KnowledgeRetrieveRequest, KnowledgeRetrieveResult
from app.settings import settings


DEFAULT_DIFY_API_BASE_URL = "http://10.30.11.215:9879"
DEFAULT_RERANKING_PROVIDER = "langgenius/siliconflow/siliconflow"
DEFAULT_RERANKING_MODEL = "netease-youdao/bce-reranker-base_v1"
DEFAULT_EMBEDDING_PROVIDER = "langgenius/siliconflow/siliconflow"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"


def dify_enabled() -> bool:
    return settings.chatbi_dify_enabled


def dify_base_url() -> str:
    return settings.dify_api_base_url


def dify_api_key_configured() -> bool:
    return bool(settings.dify_api_key)


def resolve_dataset(name_or_id: str) -> tuple[str, dict[str, Any]]:
    dataset_id = DIFY_DATASET_ALIASES.get(name_or_id, name_or_id)
    info = DIFY_DATASETS.get(dataset_id, {"name": dataset_id, "description": "未知知识库", "use_cases": []})
    return dataset_id, info


def build_retrieval_payload(request: KnowledgeRetrieveRequest) -> dict[str, Any]:
    retrieval_model: dict[str, Any] = {
        "search_method": request.search_method,
        "top_k": request.top_k,
        "score_threshold_enabled": request.score_threshold_enabled,
        "reranking_enable": request.reranking_enable,
    }

    if request.score_threshold_enabled:
        retrieval_model["score_threshold"] = request.score_threshold

    if request.reranking_enable:
        retrieval_model["reranking_model"] = {
            "reranking_provider_name": settings.dify_reranking_provider or DEFAULT_RERANKING_PROVIDER,
            "reranking_model_name": settings.dify_reranking_model or DEFAULT_RERANKING_MODEL,
        }
    elif request.search_method == "hybrid_search":
        vector_weight = round(request.vector_weight, 2)
        retrieval_model["weights"] = {
            "weight_type": "customized",
            "vector_setting": {
                "vector_weight": vector_weight,
                "embedding_provider_name": settings.dify_embedding_provider or DEFAULT_EMBEDDING_PROVIDER,
                "embedding_model_name": settings.dify_embedding_model or DEFAULT_EMBEDDING_MODEL,
            },
            "keyword_setting": {"keyword_weight": round(1 - vector_weight, 2)},
        }

    return {"query": request.query, "retrieval_model": retrieval_model}


def dify_config_metadata() -> dict[str, Any]:
    return {
        "enabled": dify_enabled(),
        "provider": "dify" if dify_enabled() else "mock-dify",
        "base_url": dify_base_url(),
        "api_key_configured": dify_api_key_configured(),
        "datasets": [
            {"id": dataset_id, **info}
            for dataset_id, info in DIFY_DATASETS.items()
        ],
        "defaults": {
            "dataset": "国际问答对-V3",
            "search_method": "semantic_search",
            "top_k": 3,
            "score_threshold_enabled": False,
            "reranking_enable": False,
        },
    }


async def retrieve_knowledge(request: KnowledgeRetrieveRequest) -> KnowledgeRetrieveResult:
    dataset_id, dataset_info = resolve_dataset(request.dataset_id)
    payload = build_retrieval_payload(request)

    if not dify_enabled() or not dify_api_key_configured():
        return mock_retrieve_result(request, dataset_id, dataset_info, payload)

    url = f"{dify_base_url()}/v1/datasets/{dataset_id}/retrieve"

    try:
        data = await asyncio.to_thread(post_dify_json, url, payload)
    except Exception as exc:
        return mock_retrieve_result(
            request,
            dataset_id,
            dataset_info,
            payload,
            fallback_reason=f"real Dify retrieve failed: {type(exc).__name__}: {exc!s}",
        )

    return KnowledgeRetrieveResult(
        query=request.query,
        dataset_id=dataset_id,
        dataset_name=dataset_info["name"],
        provider="dify",
        search_method=request.search_method,
        top_k=request.top_k,
        records=normalize_dify_records(data),
        request_payload=payload,
    )


def post_dify_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    parsed = urlsplit(url)
    connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn = connection_cls(parsed.hostname, parsed.port, timeout=30)
    try:
        conn.request(
            "POST",
            path,
            body=body,
            headers={
                "Authorization": f"Bearer {settings.dify_api_key}",
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )
        response = conn.getresponse()
        response_body = response.read()
        if response.status >= 400:
            detail = response_body.decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {response.status}: {detail}")
        return json.loads(response_body.decode("utf-8"))
    finally:
        conn.close()


def mock_retrieve_result(
    request: KnowledgeRetrieveRequest,
    dataset_id: str,
    dataset_info: dict[str, Any],
    payload: dict[str, Any],
    fallback_reason: str | None = None,
) -> KnowledgeRetrieveResult:
    records = MOCK_DIFY_RECORDS[: request.top_k]
    reason = fallback_reason or "CHATBI_DIFY_ENABLED is false or DIFY_API_KEY is not configured"
    return KnowledgeRetrieveResult(
        query=request.query,
        dataset_id=dataset_id,
        dataset_name=dataset_info["name"],
        provider="mock-dify",
        search_method=request.search_method,
        top_k=request.top_k,
        records=records,
        fallback={"strategy": "mock_dify_retrieve", "reason": reason},
        request_payload=payload,
    )


def normalize_dify_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("records", [])
    normalized = []
    for record in records:
        segment = record.get("segment") or {}
        normalized.append(
            {
                "segment_id": segment.get("id") or record.get("id"),
                "document_name": segment.get("document", {}).get("name") or record.get("document_name"),
                "content": segment.get("content") or record.get("content", ""),
                "score": record.get("score"),
                "metadata": segment.get("metadata") or record.get("metadata") or {},
                "raw": record,
            }
        )
    return normalized
