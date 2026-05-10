# ChatBI 开发规格说明书（完整版·上）

> **版本**: v2.0 — 经 10 轮内部逻辑推演与交叉验证后的最终版
> **面向对象**: AI Coding Agent / 开发者
> **审计基线**: 优化版流程图、Dify YAML 工作流 ×2、Dify 知识库 API 文档、前端原型 index_robot_only.html、记忆架构设计文档

---

## 1. 项目概览

### 1.1 产品定义
**广汽国际 AI 数据助手 (GAC AI Assistant)** —— 嵌入式悬浮 AI 机器人，可放置在任意页面（集团驾驶舱系统），为广汽国际业务用户提供自然语言数据查询与分析。

### 1.2 核心能力
| 能力 | 说明 |
|------|------|
| 快速问答 | 用户提问 → SQL → 数据 + ECharts 可视化 |
| 深度思考 | 用户提问 → SQL → 数据 + 深度分析报告 |
| 闲聊 | 非数据类问题的友好回答 |
| 追问 | 基于前文继续追问（"那华东区呢"） |
| 反问澄清 | 意图不明时主动反问用户 |
| 用户记忆 | 跨会话记住用户偏好与查询习惯 |
| 数据权限 | 不同账号按表级权限隔离数据访问 |

### 1.3 关键约束
- **账号体系**：接入集团驾驶舱权限管理，用户有 `user_id` + 可访问表列表
- **数据安全**：接触业务数据的节点必须用广汽云自部署模型，防泄露
- **Dify 仅知识库检索**：工作流全部由 LangGraph 编排
- **目标用户**：几百人日活，内网部署
- **不实现"导数助手"**：前端原型中的第二个 Tab 不在本期范围

---

## 2. 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | React 18 + Vite | 悬浮机器人组件，ECharts 5 渲染 |
| 后端 API | FastAPI | WebSocket 流式 + REST API |
| 编排引擎 | LangGraph ≥ 0.2 | 核心工作流 |
| LLM 框架 | LangChain | OpenAI-compatible 接口调用 |
| 主力模型 | DeepSeek-V3.1 | 外部 + 自部署两套 |
| 知识库 | Dify Retrieve API | 仅检索 |
| 业务数据库 | MySQL | 广汽业务数据 |
| 应用数据库 | SQLite(dev) / PostgreSQL(prod) | 会话/记忆/历史 |
| MCP | mcp-server-starrocks | Phase 3 集成 |

---

## 3. 项目目录结构

```
ChatBI/
├── .env.example / .env
├── docker-compose.yml
├── server/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # .env 加载
│   ├── api/
│   │   ├── routes.py              # REST (历史/会话)
│   │   └── websocket.py           # WS 流式对话
│   ├── auth/
│   │   └── permissions.py         # 表级权限过滤 + SQL 表引用验证
│   ├── graph/
│   │   ├── state.py               # ChatBIState
│   │   ├── builder.py             # Graph 构建+编译
│   │   ├── edges.py               # 条件路由函数
│   │   └── nodes/
│   │       ├── initialize.py      # 初始化 + 加载记忆
│   │       ├── intent.py          # 意图识别(含置信度)
│   │       ├── clarify.py         # 低置信度反问
│   │       ├── chat.py            # 闲聊
│   │       ├── context.py         # 上下文补全
│   │       ├── task_builder.py    # 构建分析任务
│   │       ├── support_check.py   # 可支持性校验
│   │       ├── support_resp.py    # 不支持时的友好提示
│   │       ├── knowledge.py       # Dify 知识库检索
│   │       ├── schema.py          # Schema 组装(按权限过滤)
│   │       ├── sql_gen.py         # SQL 生成
│   │       ├── sql_guard.py       # SQL 安全门禁 + 表权限二次验证
│   │       ├── sql_repair.py      # SQL 自我修正
│   │       ├── sql_exec.py        # SQL 执行
│   │       ├── data_analyze.py    # 快速=EChart / 深度=报告
│   │       ├── metric_explain.py  # 口径说明
│   │       ├── save_memory.py     # 沉淀用户记忆
│   │       └── fail.py            # 全局失败兜底
│   ├── services/
│   │   ├── llm.py                 # 双模型工厂(外部/内部)
│   │   ├── dify_kb.py             # Dify 知识库检索
│   │   └── database.py            # 业务 DB 执行
│   └── storage/
│       ├── checkpointer.py        # 会话记忆
│       ├── store.py               # 用户记忆(Store)
│       └── history.py             # 历史记录 CRUD
├── client/
│   ├── package.json / vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── index.css
│       ├── components/
│       │   ├── Launcher.jsx       # 悬浮按钮
│       │   ├── ChatPanel.jsx      # 主面板
│       │   ├── ChatHeader.jsx     # 头部(新对话/展开/关闭)
│       │   ├── MessageList.jsx
│       │   ├── MessageBubble.jsx  # 含进度指示/Markdown/SQL/图表
│       │   ├── InputBar.jsx
│       │   ├── ModeSwitch.jsx     # 快速问答↔深度思考
│       │   ├── HistoryDrawer.jsx  # 搜索+删除
│       │   ├── ChartRenderer.jsx  # ECharts
│       │   └── ThinkingBlock.jsx  # 深度思考折叠块
│       ├── hooks/
│       │   ├── useWebSocket.js    # WS + 心跳 + 自动重连
│       │   └── useChat.js
│       └── utils/api.js
```

---

## 4. 环境变量 (.env)

```env
# === LLM 模型 (外部 - 意图/闲聊/消解) ===
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://your-endpoint/v1
DEEPSEEK_MODEL=DeepSeek-V3.1

# === LLM 模型 (内部自部署 - SQL/数据分析, 防数据泄露) ===
INTERNAL_LLM_API_KEY=sk-xxx
INTERNAL_LLM_BASE_URL=https://gac-cloud-internal/v1
INTERNAL_LLM_MODEL=DeepSeek-V3.1

# === Dify 知识库 ===
DIFY_API_KEY=dataset-S5L6smkj8ovnSz8rMl5DZUvj
DIFY_BASE_URL=http://10.30.11.215:9879/v1
DIFY_DATASET_IDS=9e07fcf2-56cf-4f2c-b115-8727e721fbd3,486476a8-15f6-4359-bcb5-6efd40d90373,90560d64-db69-4c66-88ca-9c86a340dd5d,ffa84ba6-4ec9-44a0-8f6d-594b27f7a829,959f346f-f950-480c-a1d7-d792ad10be33

# === 业务数据库 ===
DATABASE_URI=mysql+pymysql://user:pass@host:port/db_name

# === 应用数据库 ===
APP_DATABASE_URI=sqlite:///./chatbi.db

# === 服务配置 ===
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=INFO
MAX_SQL_REPAIR_COUNT=3

# === 前端 (client/.env) ===
# VITE_WS_URL=ws://localhost:8000/ws/chat
# VITE_API_URL=http://localhost:8000/api
```

---

## 5. LangGraph State

```python
# server/graph/state.py
from typing import TypedDict, Literal, Optional, Annotated
from langgraph.graph.message import add_messages

class ChatBIState(TypedDict):
    messages: Annotated[list, add_messages]

    # 用户上下文
    user_id: str
    mode: Literal["quick", "deep"]
    allowed_tables: list[str]

    # 意图识别
    intent: Optional[Literal["chat", "data", "followup", "clarify"]]
    confidence: Optional[float]

    # 用户记忆
    user_memories: list[dict]

    # 任务构建
    resolved_query: Optional[str]
    bi_task: Optional[str]

    # 知识检索
    knowledge_context: Optional[str]
    schema_context: Optional[str]

    # SQL 链路
    sql: Optional[str]
    guard_result: Optional[Literal["safe", "repairable", "malicious"]]  # 三态(非bool)
    sql_error: Optional[str]
    repair_count: int
    query_result: Optional[str]

    # 输出
    analysis: Optional[str]
    echart_option: Optional[str]
    deep_report: Optional[str]
    metric_explanation: Optional[str]
    error_message: Optional[str]
    current_time: Optional[str]
```

> **Review Fix #4**: `guard_result` 使用三态 Literal 替代 `sql_safe: bool`，避免 None 歧义。

---

## 6. Graph 构建（含 compile 示例）

```python
# server/graph/builder.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore
from .state import ChatBIState
from .nodes import *
from .edges import *

def build_graph():
    builder = StateGraph(ChatBIState)

    # ─── 注册节点（19个，含 support_resp 独立节点）───
    builder.add_node("initialize", initialize_node)
    builder.add_node("intent", intent_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("chat", chat_node)
    builder.add_node("context", context_node)
    builder.add_node("task_builder", task_builder_node)
    builder.add_node("support_check", support_check_node)
    builder.add_node("support_resp", support_resp_node)   # Fix #7: 独立友好提示节点
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("schema", schema_node)
    builder.add_node("sql_gen", sql_gen_node)
    builder.add_node("sql_guard", sql_guard_node)
    builder.add_node("sql_repair", sql_repair_node)
    builder.add_node("sql_exec", sql_exec_node)
    builder.add_node("data_analyze", data_analyze_node)
    builder.add_node("metric_explain", metric_explain_node)
    builder.add_node("save_memory", save_memory_node)
    builder.add_node("fail", fail_node)

    # ─── 边 ───
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "intent")

    builder.add_conditional_edges("intent", route_after_intent, {
        "chat": "chat",
        "data": "task_builder",
        "followup": "context",
        "clarify": "clarify",
    })

    builder.add_edge("chat", END)
    builder.add_edge("clarify", END)
    builder.add_edge("context", "task_builder")

    builder.add_edge("task_builder", "support_check")
    builder.add_conditional_edges("support_check", route_after_support, {
        "supported": "knowledge",
        "unsupported": "support_resp",      # Fix #7: → 友好提示
    })
    builder.add_edge("support_resp", END)

    builder.add_edge("knowledge", "schema")
    builder.add_conditional_edges("schema", route_after_schema, {
        "found": "sql_gen",
        "not_found": "support_resp",        # Fix #8: schema_not_found → 友好提示
    })

    # Fix #1: sql_gen 加条件边处理生成失败
    builder.add_conditional_edges("sql_gen", route_after_sql_gen, {
        "success": "sql_guard",
        "error": "fail",
    })

    builder.add_conditional_edges("sql_guard", route_after_guard, {
        "safe": "sql_exec",
        "repairable": "sql_repair",
        "malicious": "fail",
    })

    builder.add_conditional_edges("sql_repair", route_after_repair, {
        "retry": "sql_guard",
        "exceeded": "fail",
    })

    builder.add_conditional_edges("sql_exec", route_after_exec, {
        "success": "data_analyze",
        "sql_error": "sql_repair",
        "fatal": "fail",
    })

    builder.add_edge("data_analyze", "metric_explain")
    builder.add_edge("metric_explain", "save_memory")
    builder.add_edge("save_memory", END)
    builder.add_edge("fail", END)

    return builder


# ─── Fix #12: 编译示例（含 Store + Checkpointer）───
async def compile_graph():
    """开发环境用 SQLite + InMemoryStore"""
    store = InMemoryStore()
    checkpointer = AsyncSqliteSaver.from_conn_string("./chatbi_checkpoints.db")
    await checkpointer.setup()

    builder = build_graph()
    graph = builder.compile(
        checkpointer=checkpointer,
        store=store,
    )
    return graph
```

---

## 7. 条件路由函数

```python
# server/graph/edges.py
import os

def route_after_intent(state) -> str:
    if state["intent"] == "chat":
        return "chat"
    if state.get("confidence", 1.0) < 0.5:
        return "clarify"
    if state["intent"] == "followup":
        return "followup"
    return "data"

def route_after_support(state) -> str:
    return "supported" if state.get("bi_task") else "unsupported"

def route_after_schema(state) -> str:
    return "found" if state.get("schema_context") else "not_found"

# Fix #1: sql_gen 路由
def route_after_sql_gen(state) -> str:
    return "success" if state.get("sql") else "error"

# Fix #4: 使用三态 guard_result
def route_after_guard(state) -> str:
    return state.get("guard_result", "repairable")

def route_after_repair(state) -> str:
    max_repairs = int(os.getenv("MAX_SQL_REPAIR_COUNT", "3"))
    return "exceeded" if state["repair_count"] >= max_repairs else "retry"

def route_after_exec(state) -> str:
    if state.get("query_result"):
        return "success"
    if state.get("sql_error") and state["repair_count"] < int(os.getenv("MAX_SQL_REPAIR_COUNT", "3")):
        return "sql_error"
    return "fatal"
```

---

## 8. 关键节点实现规格

### 8.1 initialize_node
```python
async def initialize_node(state, *, store):
    from datetime import datetime
    import pytz
    now = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    user_id = state["user_id"]
    memories = []
    if store:
        items = await store.asearch(
            namespace=(user_id, "preferences"),
            query=state["messages"][-1].content if state["messages"] else "",
            limit=5
        )
        memories = [item.value for item in items]

    return {"current_time": now, "user_memories": memories, "repair_count": 0}
```

### 8.2 intent_node
- **模型**: 外部 DeepSeek-V3.1
- **输出**: structured JSON → `{"intent": "...", "confidence": 0.x, "reason": "..."}`
- **置信度逻辑**: `≥0.8` 直接用 / `0.5~0.8` 结合记忆再判断 / `<0.5` → clarify

### 8.3 knowledge_node (Dify 检索)
```python
async def knowledge_node(state):
    query = state.get("resolved_query") or state["messages"][-1].content
    payload = {
        "query": query,
        "retrieval_model": {
            "search_method": "hybrid_search",
            "top_k": 5,
            "score_threshold_enabled": True,
            "score_threshold": 0.3,
            "reranking_enable": True,
            "reranking_model": {
                "reranking_provider_name": "langgenius/siliconflow/siliconflow",
                "reranking_model_name": "netease-youdao/bce-reranker-base_v1"
            }
        }
    }
    dataset_ids = os.getenv("DIFY_DATASET_IDS", "").split(",")
    results = []
    for ds_id in dataset_ids:
        resp = await dify_client.retrieve(ds_id.strip(), payload)
        results.extend(resp.get("records", []))
    context = "\n".join([r["segment"]["content"] for r in results])
    return {"knowledge_context": context}
```

### 8.4 schema_node — 按用户权限过滤 DDL
### 8.5 sql_gen_node — 自部署模型 + 7条黄金准则 (从 Dify YAML 迁移)
### 8.6 sql_guard_node — 正则检测 + **表权限二次验证** (Fix #9)
```python
async def sql_guard_node(state):
    sql = state["sql"]
    DANGEROUS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]
    sql_upper = sql.upper()

    # 检测恶意操作
    if any(kw in sql_upper for kw in DANGEROUS):
        return {
            "guard_result": "malicious",
            "error_message": "检测到危险SQL操作（如DELETE/DROP），请求已被安全系统拒绝。"
        }

    # Fix #9: 二次验证 SQL 引用的表是否在用户权限范围内
    from auth.permissions import validate_sql_tables
    if not validate_sql_tables(sql, state["allowed_tables"]):
        return {
            "guard_result": "malicious",
            "error_message": "查询涉及未授权的数据表，请联系管理员开通权限。"
        }

    # 基础语法检查
    if not sql_upper.strip().startswith("SELECT"):
        return {"guard_result": "repairable", "sql_error": "SQL必须以SELECT开头"}

    return {"guard_result": "safe"}
```

### 8.7 data_analyze_node (Fix #2: 修正 LLM 返回对象处理)
```python
async def data_analyze_node(state):
    llm = get_internal_llm()  # 自部署模型
    query_result = state["query_result"]
    resolved_query = state.get("resolved_query") or state["messages"][-1].content

    if state["mode"] == "quick":
        prompt = f"""...(省略，见下册 §11.3)..."""
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        # Fix #2: 正确解析 LLM 返回
        import json
        try:
            parsed = json.loads(response.content)
            return {"analysis": parsed["analysis"], "echart_option": json.dumps(parsed["echart_option"])}
        except (json.JSONDecodeError, KeyError):
            # Fix: 降级容错 - 直接用文本作为 analysis
            return {"analysis": response.content, "echart_option": None}
    else:
        prompt = f"""...(省略，见下册 §11.4)..."""
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        return {"deep_report": response.content}
```

### 8.8 save_memory_node (Fix #3: 修正 state 字段引用)
```python
async def save_memory_node(state, *, store):
    if not store:
        return {}
    user_id = state["user_id"]
    user_query = state.get("resolved_query") or state["messages"][-1].content  # Fix #3

    extraction_prompt = f"""分析以下对话，提取值得记忆的用户偏好：
用户问题: {user_query}
意图: {state.get('intent')}
SQL: {state.get('sql', 'N/A')}
输出 JSON 数组: [{{"category": "preferences|query_patterns", "content": "..."}}]"""

    llm = get_external_llm()
    result = await llm.ainvoke([{"role": "user", "content": extraction_prompt}])
    # 解析并存入 Store...
    return {}
```

### 8.9 support_resp_node (Fix #7: 独立友好提示)
```python
async def support_resp_node(state):
    """不支持的查询返回友好提示，区别于系统故障的 fail_node"""
    return {
        "error_message": "抱歉，我暂时不支持查询这类数据。请尝试换一种问法，或联系数据团队确认数据范围。"
    }
```
