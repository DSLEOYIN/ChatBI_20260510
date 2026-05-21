from typing import Any, Literal

from pydantic import BaseModel, Field


Intent = Literal[
    "chat",
    "simple_query",
    "analysis",
    "comparison",
    "alert",
    "definition",
    "search",
]


class ConversationCreate(BaseModel):
    user_id: str = "demo_user"


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    content: str = Field(min_length=1)
    conversation_id: str | None = None
    user_id: str = "demo_user"
    mode: Literal["quick", "deep"] = "quick"
    web_search: bool = False


StreamEventType = Literal["conversation_id", "step", "sql", "answer", "canvas", "done", "error"]
CanvasComponentType = Literal["answer", "kpi", "kpi_grid", "chart", "table", "risk", "definition", "search_results", "insight"]


class StreamEvent(BaseModel):
    type: StreamEventType
    data: Any = None


class ExecutionStep(BaseModel):
    name: str
    status: Literal["done", "warning", "error"]
    detail: str
    tool: str | None = None
    duration: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class CanvasComponent(BaseModel):
    id: str
    type: CanvasComponentType
    title: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class CanvasPayload(BaseModel):
    title: str
    subtitle: str
    intent: Intent
    components: list[CanvasComponent] = Field(default_factory=list)


class ChatResult(BaseModel):
    conversation_id: str
    intent: Intent
    answer: str
    visible_steps: list[ExecutionStep]
    sql: str | None = None
    canvas: CanvasPayload


class SearchMockResult(BaseModel):
    query: str
    provider: str = "mock-tavily"
    search_depth: Literal["basic", "advanced"] = "advanced"
    include_answer: bool = True
    answer: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    fallback: dict[str, Any] | None = None
