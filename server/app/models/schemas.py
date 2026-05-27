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


class LlmTestRequest(BaseModel):
    prompt: str = Field(default="请用一句话说明 DeepSeek LLM 已经连通。", min_length=1)
    system_prompt: str = "你是 ChatBI 的后端连通性测试助手，请用简短中文回答。"
    temperature: float = Field(default=0.1, ge=0, le=2)


class LlmTestResult(BaseModel):
    provider: str
    id: str | None = None
    model: str
    content: str
    finish_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class SqlGenerateRequest(BaseModel):
    question: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0, le=2)


class SqlGenerateResult(BaseModel):
    provider: str
    model: str
    sql: str
    validation: dict[str, Any]
    finish_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


StreamEventType = Literal["conversation_id", "step", "sql", "answer", "canvas", "done", "error"]
CanvasComponentType = Literal["answer", "kpi", "kpi_grid", "chart", "table", "risk", "definition", "search_results", "insight"]


class StreamEvent(BaseModel):
    type: StreamEventType
    data: Any = None
    sequence: int | None = None
    emitted_at: str | None = None


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


RetrievalSearchMethod = Literal["semantic_search", "keyword_search", "hybrid_search"]


class KnowledgeRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    dataset_id: str = "国际问答对-V3"
    search_method: RetrievalSearchMethod = "semantic_search"
    top_k: int = Field(default=3, ge=1, le=20)
    score_threshold_enabled: bool = False
    score_threshold: float = Field(default=0.5, ge=0, le=1)
    reranking_enable: bool = False
    vector_weight: float = Field(default=0.7, ge=0, le=1)


class KnowledgeRetrieveResult(BaseModel):
    query: str
    dataset_id: str
    dataset_name: str
    provider: str
    search_method: RetrievalSearchMethod
    top_k: int
    records: list[dict[str, Any]] = Field(default_factory=list)
    fallback: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None


class SqlValidationResult(BaseModel):
    valid: bool
    sql: str
    tables: list[str] = Field(default_factory=list)
    allowed_tables: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    sql: str = Field(min_length=1)
    limit: int = Field(default=200, ge=1, le=1000)


class QueryResult(BaseModel):
    provider: Literal["mock", "mysql"]
    sql: str
    validation: SqlValidationResult
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    elapsed_ms: int
    connection: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
