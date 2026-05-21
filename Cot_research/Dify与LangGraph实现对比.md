# Dify 与 LangGraph CoT 实现对比

> 双轨制架构分析

---

## 一、架构定位

| 维度 | Dify 工作流 | LangGraph |
|------|-------------|-----------|
| **定位** | 深度思考模式（V3.0） | 快速问答模式（主架构） |
| **编排方式** | YAML 配置 + 可视化编辑器 | Python 代码 + 状态机 |
| **适用场景** | 复杂分析流程、报告生成 | 高并发实时查询 |
| **优势** | 低代码、拖拽配置 | 灵活、代码可控 |
| **扩展方式** | 节点市场 / 自定义节点 | Python 函数 / @tool 装饰器 |

---

## 二、Dify 深度思考 V3.0 工作流

### 2.1 节点列表

```
开始 → 获取时间 → 记录时间
              ↓
         意图识别 LLM → 意图分支 if-else
              ↓              ↓
         闲聊分支       数据分析分支
              ↓              ↓
         闲聊节点      首次回复
              ↓              ↓
         闲聊回复      知识检索-字段标准查询名
              ↓              ↓
                       提取标准查询信息
              ↓              ↓
                       知识检索-同环比（条件触发）
              ↓              ↓
                       N2SQL-同环比
              ↓              ↓
                       N2SQL 聚合
              ↓              ↓
                       AI 生成 SQL 语句 → SQL数据获取判断
                              ↓                    ↓
                    数据为空回复-1          数据查询完成
                              ↓                    ↓
                         [结束]            数据解读 LLM
                                                   ↓
                                            大模型写口径
                                                   ↓
                                              数据解读回复
                                                   ↓
                                                [结束]
```

### 2.2 SQL 修正循环（Dify 实现）

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  AI 生成 SQL  ──→  首次-SQL语句查询  ──→  SQL数据判断    │
│       ↑                                        ↓         │
│       │                                   [sql_text为空] │
│       │                                        ↓         │
│       │                                 数据为空回复-1   │
│       │                                        ↓         │
│       │                                      [结束]      │
│       │                                              │
│       │               ┌─────────────────────────┐      │
│       └───────────────┤    第二次-SQL语句查询    │      │
│                       └───────────┬─────────────┘      │
│                                   ↓                    │
│                           SQL数据获取判断               │
│                                   ↓                    │
│                         [sql_text为空] ──→ [结束]       │
│                                   ↓                    │
│                               [继续]                   │
│                                   ↓                    │
│                              SQL 修正节点               │
│                                   ↓                    │
│                        第三次-SQL语句查询               │
│                                   ↓                    │
│                              SQL数据判断                 │
│                                   ↓                    │
│                         [sql_text为空] ──→ [结束]       │
│                                   ↓                    │
│                               [继续]                   │
│                                   ↓                    │
│                              数据解读                    │
└──────────────────────────────────────────────────────────┘
```

### 2.3 Dify 关键 Prompt 模板

**SQL 生成黄金准则**（节点 1750061504284）：
```
# 黄金准则 0：优先参考上下文
# 黄金准则 1：广汽国际默认不加 where 条件
# 黄金准则 2：只返回纯 SQL，禁止解释
# 黄金准则 3：严禁 JOIN，用子查询替代
# 黄金准则 4：所有输出列加中文别名
# 黄金准则 5：尊重时间聚合层级
# 黄金准则 6：库存/订单取时间段最后一天
# 黄金准则 7：比例指标保留两位小数 + %
```

**SQL 修正 Prompt**（节点 1759047065164）：
```
Role: SQL Debugging Expert

分析：用户问题 + 错误SQL + 报错信息 + 错误类型
要求：先分析原因，再制定优化计划，最后执行修正
输出：仅返回修正后的纯 SQL
```

---

## 三、LangGraph 主架构

### 3.1 节点定义（builder.py）

```python
NODES = [
    "initialize",      # 初始化 + 加载记忆
    "intent",         # 意图识别（含置信度）
    "clarify",        # 低置信度反问
    "chat",           # 闲聊
    "context",        # 上下文补全（追问）
    "task_builder",   # 构建分析任务
    "support_check",  # 可支持性校验
    "support_resp",   # 不支持时的友好提示
    "knowledge",      # Dify 知识库检索
    "schema",         # Schema 组装（按权限过滤）
    "sql_gen",        # SQL 生成
    "sql_guard",      # SQL 安全门禁 + 表权限验证
    "sql_repair",     # SQL 自我修正
    "sql_exec",       # SQL 执行
    "data_analyze",   # 快速=EChart / 深度=报告
    "metric_explain", # 口径说明
    "save_memory",    # 沉淀用户记忆
    "fail",           # 全局失败兜底
]
```

### 3.2 边定义（与 Dify 对比）

| LangGraph 边 | Dify 等价节点/连接 |
|--------------|-------------------|
| START → initialize | 开始节点 |
| initialize → intent | 自动触发 |
| intent → chat/clarify/task_builder/context | 意图分支 if-else |
| task_builder → support_check | 任务构建节点 |
| support_check → knowledge/support_resp | 支持性判断 |
| knowledge → schema | 知识检索结果 |
| schema → sql_gen/support_resp | Schema 判断 |
| sql_gen → sql_guard/fail | SQL 生成判断 |
| sql_guard → sql_exec/sql_repair/malicious | SQL 安全判断 |
| sql_repair → sql_guard/exceeded | SQL 修正循环 |
| sql_exec → data_analyze/sql_repair/fail | 执行结果判断 |
| data_analyze → metric_explain | 数据分析完成 |
| metric_explain → save_memory | 口径说明完成 |
| save_memory → END | 结束 |

---

## 四、关键差异

| 特性 | Dify | LangGraph |
|------|------|-----------|
| **修正循环** | 固定 2-3 次重试 | 可配置 `MAX_SQL_REPAIR_COUNT` |
| **状态管理** | 隐式（节点变量） | 显式（ChatBIState TypedDict） |
| **路由逻辑** | YAML 配置 | Python 函数 |
| **记忆管理** | Dify 原生 | LangGraph Store + Checkpointer |
| **权限控制** | Dify 数据集权限 | 代码层面 `validate_sql_tables` |
| **部署复杂度** | 低（Docker 一键部署） | 中（需要 Python 环境） |
| **调试方式** | Dify 运行日志 | Python logging |

---

## 五、融合建议

### 5.1 短期（当前架构）
- **快速问答**：LangGraph 主流程
- **深度分析**：调用 Dify API

```python
# LangGraph 中调用 Dify
async def deep_think_node(state):
    # 调用 Dify 深度思考工作流
    dify_result = await dify_client.run_workflow(
        workflow_id="deep-think-v3",
        input={"query": state["messages"][-1].content}
    )
    return {"deep_report": dify_result["output"]}
```

### 5.2 长期（统一架构）
```
┌─────────────────────────────────────┐
│         Main Orchestrator           │
│        (LangGraph 状态机)           │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
   ┌─────────┐   ┌─────────────┐
   │ 简单查询 │   │ 复杂分析     │
   │(LangGraph│   │(Dify Workflow│
   │  直接跑) │   │   API)       │
   └─────────┘   └─────────────┘
```

---

*文档版本：v1.0 | 2026-05-21*
