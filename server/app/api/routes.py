import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.mock.catalog import DATA_ASSETS, SKILLS
from app.mock.engine import build_result, detail_csv, make_conversation, stream_result
from app.models.schemas import ChatRequest, ConversationCreate
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
    return DATA_ASSETS


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
        async for event in stream_result(result):
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


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
