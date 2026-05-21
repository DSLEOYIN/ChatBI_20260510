import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.mock.catalog import (
    CANVAS_PAYLOAD_SCHEMA,
    DATA_ASSETS,
    DOWNLOAD_CONTRACT,
    METRIC_DEFINITIONS,
    SKILLS,
)
from app.mock.engine import build_result, detail_csv, make_conversation, mock_search, stream_result
from app.models.schemas import ChatRequest, ConversationCreate, SearchMockResult
from app.storage import (
    append_exchange,
    create_conversation_record,
    delete_conversation_record,
    get_conversation_record,
    list_conversation_records,
    pin_conversation_record,
)

router = APIRouter(prefix="/api")

@router.get("/health")
async def health():
    return {"status": "ok", "service": "chatbi-mock"}


@router.post("/conversations")
async def create_conversation(payload: ConversationCreate):
    conversation = make_conversation(payload.user_id)
    create_conversation_record(conversation)
    return without_messages(conversation)


@router.get("/conversations")
async def list_conversations(user_id: str = "demo_user"):
    return list_conversation_records(user_id)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = get_conversation_record(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    delete_conversation_record(conversation_id)
    return {"ok": True}


@router.post("/conversations/{conversation_id}/pin")
async def pin_conversation(conversation_id: str, pinned: bool):
    pin_conversation_record(conversation_id, pinned)
    return {"ok": True}


@router.get("/config/skills")
async def skills():
    return SKILLS


@router.get("/config/data-assets")
async def data_assets():
    return {"assets": DATA_ASSETS, "metric_definitions": METRIC_DEFINITIONS}


@router.get("/config/canvas-schema")
async def canvas_schema():
    return CANVAS_PAYLOAD_SCHEMA


@router.get("/config/download-contract")
async def download_contract():
    return DOWNLOAD_CONTRACT


@router.get("/mock/search", response_model=SearchMockResult)
async def search_mock(q: str = "中东 SUV 市场 竞品 促销"):
    return mock_search(q)


@router.post("/chat")
async def chat(payload: ChatRequest):
    conversation_id = ensure_conversation(payload)
    result = build_result(payload, conversation_id)
    save_exchange(conversation_id, payload.content, result.model_dump())
    return result


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    conversation_id = ensure_conversation(payload)
    result = build_result(payload, conversation_id)
    save_exchange(conversation_id, payload.content, result.model_dump())

    async def event_source():
        try:
            async for event in stream_result(result):
                payload_json = json.dumps(event.model_dump(), ensure_ascii=False)
                yield f"event: {event.type}\ndata: {payload_json}\n\n"
        except Exception as exc:
            error = {"type": "error", "data": {"message": str(exc)}}
            yield f"event: error\ndata: {json.dumps(error, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/downloads/mock-detail.csv")
async def download_detail():
    return PlainTextResponse(
        detail_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=chatbi_mock_detail.csv"},
    )


def ensure_conversation(payload: ChatRequest) -> str:
    if payload.conversation_id and get_conversation_record(payload.conversation_id):
        return payload.conversation_id
    conversation = make_conversation(payload.user_id, payload.content[:18] or "新对话")
    create_conversation_record(conversation)
    return conversation["id"]


def save_exchange(conversation_id: str, user_content: str, result: dict):
    append_exchange(conversation_id, user_content, result)


def without_messages(conversation: dict) -> dict:
    return {k: v for k, v in conversation.items() if k != "messages"}
