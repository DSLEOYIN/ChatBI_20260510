# ChatBI 开发规格说明书（完整版·下）

## 9. API 设计

### 9.1 WebSocket 流式对话
```
WS /ws/chat

# 客户端发送
{
    "type": "message",
    "content": "2024年中东公司终端量是多少",
    "thread_id": "abc-123",       # 新对话不传，服务端生成
    "user_id": "user_42",
    "mode": "quick",              # quick | deep
    "allowed_tables": ["v_dm_sal_wolesale_terminal_dly", ...]
}

# 服务端流式返回（按顺序）
{"type": "thread_id", "data": "abc-123"}
{"type": "node_start", "node": "intent", "data": "正在理解您的问题..."}
{"type": "node_start", "node": "knowledge", "data": "检索业务知识..."}
{"type": "node_start", "node": "sql_gen", "data": "生成查询语句..."}
{"type": "sql", "data": "SELECT ..."}
{"type": "node_start", "node": "sql_exec", "data": "执行查询..."}
{"type": "node_start", "node": "data_analyze", "data": "分析数据..."}
{"type": "analysis", "data": "2024年中东公司..."}
{"type": "echart", "data": "{...}"}            # 快速模式
{"type": "deep_report", "data": "## 数据概览..."}  # 深度模式
{"type": "metric", "data": "口径说明：..."}      # Fix #6: 补充 metric 类型
{"type": "clarify", "data": "请问您想查..."}     # 反问场景
{"type": "error", "data": "抱歉..."}
{"type": "done"}

# 心跳机制 (Fix #10)
客户端每30秒发送: {"type": "ping"}
服务端回复: {"type": "pong"}
```

### 9.2 REST API
```
GET    /api/conversations?user_id=xxx              # 历史列表(分页)
GET    /api/conversations/{thread_id}/messages     # 会话消息
DELETE /api/conversations/{thread_id}              # 删除会话
GET    /api/conversations/search?q=xxx&user_id=xxx # 搜索历史
POST   /api/conversations/{thread_id}/title        # 自动生成标题
```

---

## 10. 前端组件规格

### 10.1 Launcher 悬浮按钮
- 固定定位 `fixed`, 右下角 `bottom:32px; right:32px`
- 68×68px，黑色渐变圆角按钮（参照 `index_robot_only.html`）
- 绿色在线指示点
- 点击切换 ChatPanel 显隐
- 支持拖拽

### 10.2 ChatPanel 主面板
- 440×680px，圆角28px，毛玻璃阴影
- 支持全屏展开
- **Header**: 头像 + "GAC AI 助手" + 在线状态 + 新对话按钮 + 展开按钮 + 历史按钮 + 关闭按钮
- **MessageList**: 滚动消息区
- **InputBar**: 输入框 + 发送 + ModeSwitch

### 10.3 ModeSwitch
- 位于输入框下方左侧，下拉菜单
- `⚡ 快速问答 ▾` ↔ `🧠 深度思考`
- 默认快速问答

### 10.4 MessageBubble
```
用户消息: 右对齐深色
AI消息: 左对齐浅色，包含：
  ① 节点进度条（"理解问题..." → "检索知识..." → "生成SQL..." → "执行查询..." → "分析数据..."）
  ② Markdown 渲染文本
  ③ SQL 代码块（可折叠）
  ④ ECharts 图表区（快速模式）
  ⑤ 深度报告区（深度模式，支持折叠思考过程）
  ⑥ 口径说明（折叠展示）
```

### 10.5 ChartRenderer
- 使用 `echarts` 或 `echarts-for-react`
- JSON 解析错误时 fallback 为纯文本
- 自适应容器宽度
- 保留 ECharts 原生交互（tooltip, zoom, click, legend toggle）

### 10.6 HistoryDrawer
- 右侧滑出抽屉
- 时间倒序列表，显示标题+时间
- 搜索框（关键词过滤）
- 滑动/点击删除
- 点击加载历史会话

### 10.7 新对话按钮 (Fix #15)
- 点击后清空当前消息列表
- 生成新 thread_id
- 不影响历史记录（旧会话自动保存）

### 10.8 WebSocket Hook (Fix #6, #10)
```javascript
// hooks/useWebSocket.js - 含心跳+重连+完整消息类型
function useWebSocket(url) {
  // 自动重连：断线后 1s/2s/4s 指数退避重连，最多5次
  // 心跳：每30秒发 ping
  // 消息处理：
  //   thread_id → 保存会话ID
  //   node_start → 更新进度指示器
  //   analysis → 追加文本（支持流式逐字）
  //   echart → 设置图表配置
  //   deep_report → 设置报告内容
  //   sql → 设置SQL（折叠展示）
  //   metric → 设置口径说明         ← Fix #6
  //   clarify → 显示反问气泡
  //   error → 显示错误提示
  //   done → 标记完成
}
```

---

## 11. 完整 Prompt 模板

### 11.1 意图识别
```
你是广汽国际数据分析助手的意图识别模块。

## 用户历史偏好
{user_memories}

## 历史对话
{chat_history}

## 当前用户输入
{user_input}

## 当前时间
{current_time}

## 任务
判断用户意图，输出 JSON：
{"intent": "chat" | "data" | "followup", "confidence": 0.0-1.0, "reason": "..."}

## 判断规则
- "chat": 与业务数据无关（天气/闲聊/常识）
- "data": 涉及销量/终端/库存/订单/排产等
- "followup": 基于前轮追问（"那华东区呢""换柱状图"）

## Few-shot 示例
{intent_examples_from_dify_yaml}
```

### 11.2 SQL 生成 (迁移自 Dify YAML 的 7 条黄金准则)
> 完整复用，关键替换：
> - `{{#context#}}` → `{knowledge_context}`
> - `{{#conversation.create_table_prompt_new#}}` → `{schema_context}` (已按权限过滤)
> - 增加 `{current_time}` 注入
> - **模型: 自部署模型**

### 11.3 数据分析 (快速模式)
```
你是广汽国际数据分析专家。

## 用户问题
{resolved_query}

## SQL 查询结果
{query_result}

## 任务
生成 JSON：
{
  "analysis": "2-3句数据解读",
  "echart_option": { ECharts option 对象 }
}

## ECharts 规则
- 自动选择最佳图表(bar/line/pie/组合)
- 必须包含 title, tooltip, legend, xAxis/yAxis
- 品牌色: ['#e83a30','#ff7d6f','#3498db','#2ecc71','#f39c12']
- 数据量≤5条用饼图，时序数据用折线，对比用柱状
```

### 11.4 深度思考
```
你是广汽国际高级数据分析师。

## 用户问题: {resolved_query}
## SQL 查询结果: {query_result}

## 报告结构
### 📊 数据概览 — 整体情况概述
### 🔍 关键发现 — 3~5个发现，含同比/环比
### 📈 趋势分析 — 增长/下降原因推测
### 💡 建议 — 2~3条业务建议

用专业简洁的中文撰写。
```

---

## 12. 应用数据库

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    mode TEXT DEFAULT 'quick',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    sql_text TEXT,
    echart_option TEXT,
    deep_report TEXT,
    metric_explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE user_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, category, key)
);

CREATE INDEX idx_conv_user ON conversations(user_id);
CREATE INDEX idx_msg_conv ON messages(conversation_id);
CREATE INDEX idx_memory_user ON user_memories(user_id, category);
```

---

## 13. 安全架构

### 13.1 节点 → 模型映射 (数据安全)

| 节点 | 模型 | 原因 |
|------|------|------|
| intent_node | 外部 DeepSeek | 不接触业务数据 |
| chat_node | 外部 DeepSeek | 闲聊不涉密 |
| context_node | 外部 DeepSeek | 仅指代消解 |
| sql_gen_node | **内部自部署** | 注入了表结构 |
| sql_guard_node | 规则引擎(无LLM) | 纯正则+权限校验 |
| data_analyze_node | **内部自部署** | 处理业务数据 |
| metric_explain_node | **内部自部署** | 引用了数据 |
| save_memory_node | 外部 DeepSeek | 仅提取偏好标签 |

### 13.2 数据权限 — 双重校验
1. **schema_node**: DDL 按 `allowed_tables` 过滤，LLM 只看到有权限的表
2. **sql_guard_node**: 生成后二次验证 SQL 引用的表是否全部在权限范围内

---

## 14. 8张业务表 (从 Dify YAML 提取)

| 表名 | 类型 | 说明 |
|------|------|------|
| v_dm_sal_wolesale_terminal_dly | 日表 | 批发+终端量 |
| v_dm_sal_sc_order_dly | 日表 | SC订单 |
| v_dm_sal_stock_dly | 日表 | 库存 |
| v_dm_sal_remain_order_dly | 日表 | 剩余订单 |
| v_dm_sal_scheduling_dly | 日表 | 排产 |
| v_dm_sal_wolesale_terminal_dly_v2 | 预实表 | 批发终端(含目标/达成率) |
| v_dm_sal_sc_order_dly_v2 | 预实表 | SC订单(含目标/达成率) |
| v_dm_sal_scheduling_dly_v2 | 预实表 | 排产(含目标/达成率) |

> 完整 DDL 建表语句和字段说明见 Dify YAML 的 `create_table_prompt_new` 变量。

---

## 15. MCP 集成预留 (Phase 3)

```python
# server/services/mcp_client.py
class MCPService:
    async def get_table_schema(self, table_name: str) -> str: ...
    async def validate_sql(self, sql: str) -> dict: ...
    async def get_query_plan(self, sql: str) -> str: ...
```

---

## 16. 分阶段开发计划

### Phase 1: MVP (2周)
- [ ] 项目骨架 (FastAPI + React Vite + LangGraph)
- [ ] 核心 Graph (意图→SQL→执行→分析)
- [ ] 快速问答完整链路
- [ ] **基础数据权限过滤** (Fix #11: 提前到 Phase 1)
- [ ] WebSocket 流式输出 + 心跳重连
- [ ] 悬浮机器人 UI
- [ ] ECharts 渲染
- [ ] 基础历史记录 (列表+删除)

### Phase 2: 增强 (1周)
- [ ] 深度思考模式
- [ ] 意图置信度 + 反问机制
- [ ] 用户记忆 (Store)
- [ ] SQL 安全门禁
- [ ] 历史搜索
- [ ] 会话标题自动生成

### Phase 3: 打磨 (1周)
- [ ] MCP Server 集成
- [ ] 联网搜索能力 (TODO: 需定义具体产品形态)
- [ ] PostgreSQL 迁移
- [ ] Docker 部署
- [ ] 性能优化

---

## 17. 部署

```yaml
# docker-compose.yml
services:
  backend:
    build: ./server
    ports: ["8000:8000"]
    env_file: .env
    volumes: ["./data:/app/data"]
  frontend:
    build: ./client
    ports: ["3000:80"]
    depends_on: [backend]
```

---

## 18. 关于 PostgreSQL

LangGraph 的 Checkpointer/Store 需要持久化数据库：
- **开发**: SQLite (零配置)
- **生产**: PostgreSQL (官方推荐)
- **切换方式**: 仅改 `.env` 中 `APP_DATABASE_URI` 一行

---

## 19. 10轮检查修正记录

| # | 问题 | 修正 |
|---|------|------|
| 1 | sql_gen 缺少失败边 | 加 conditional_edges |
| 2 | data_analyze LLM 返回属性错 | 用 json.loads(response.content) |
| 3 | save_memory 引用不存在字段 | 改为 resolved_query/messages |
| 4 | guard 用 bool 不够 | 改为三态 Literal guard_result |
| 5 | 缺 DATASET_IDS 配置 | 加入 .env |
| 6 | 前端 WS 漏 metric 类型 | 补充 |
| 7 | support_resp 被合并 | 恢复独立节点 |
| 8 | schema_not_found 应友好提示 | → support_resp |
| 9 | sql_guard 缺表权限验证 | 加 validate_sql_tables |
| 10 | WS 无心跳重连 | 加 ping/pong + 重连 |
| 11 | 权限在 Phase 2 太晚 | 提前到 Phase 1 |
| 12 | 缺 compile() 示例 | 补充含 store+checkpointer |
| 13 | Phase 1 错标 [x] | 全改 [ ] |
| 14 | 未排除导数助手 | 明确排除 |
| 15 | 新对话功能未说明 | 补充 §10.7 |
| 16 | 联网搜索无规格 | 标注 TODO |
