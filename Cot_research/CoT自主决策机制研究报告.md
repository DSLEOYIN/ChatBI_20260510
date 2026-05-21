# ChatBI CoT 自主决策机制研究报告

> 研究日期：2026-05-21
> 产出来源：ChatBI_20260509 项目代码库分析

---

## 一、CoT 自主决策概述

ChatBI 系统中的 CoT（Chain of Thought，思维链）自主决策是一种**分步骤逻辑演绎**机制，AI 通过逐步写出推理过程来收敛搜索空间，最终自主决定执行路径。

### 1.1 核心价值
- **避免逻辑滑坡**：逼迫 AI 直接给答案会大概率写错 SQL，分步骤推理让每一步文字成为下一步的"强有力线索"
- **可解释性**：决策过程可追溯，用户能理解 AI 为什么这么做
- **自我纠错**：通过观察（Observation）反馈，自动修正错误路径

---

## 二、决策架构总览

```
用户输入
    │
    ▼
┌─────────────────┐
│  意图识别节点    │ ◄── LLM 判断意图类型 + 置信度
│  (intent_node)  │
└────────┬────────┘
         │ 条件路由
         ├──────────────────────────────────────┐
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│    闲聊分支     │                    │   数据分析分支   │
│   (chat_node)  │                    │ (task_builder)  │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                ▼
                                      ┌─────────────────┐
                                      │  知识检索节点    │
                                      │(knowledge_node) │
                                      └────────┬────────┘
                                                │
                                                ▼
                                      ┌─────────────────┐
                                      │  Schema 组装    │
                                      │  (schema_node)  │
                                      └────────┬────────┘
                                                │ 条件路由
                                                ├─────────────────────┐
                                                ▼                     ▼
                                      ┌─────────────────┐   ┌─────────────────┐
                                      │  SQL 生成节点   │   │  不支持提示    │
                                      │  (sql_gen_node) │   │(support_resp)  │
                                      └────────┬────────┘   └─────────────────┘
                                                │
                                    ┌───────────┴───────────┐
                                    │     SQL 安全门禁      │
                                    │    (sql_guard_node)   │
                                    └───────────┬───────────┘
                                                │ 三态路由
                                                ├────────────────────────────┐
                                                ▼              ▼              ▼
                                      ┌────────────┐  ┌────────────┐  ┌────────────┐
                                      │   安全通过  │  │  可修正     │  │   恶意阻断  │
                                      │  → 执行SQL │  │  → SQL修正  │  │  → 失败节点 │
                                      └────────────┘  └─────┬──────┘  └────────────┘
                                                            │ 循环修正
                                                            ▼
                                                      ┌────────────┐
                                                      │  SQL 执行   │
                                                      │(sql_exec)  │
                                                      └─────┬──────┘
                                                            │ 结果路由
                                                            ▼
                                                      ┌────────────┐
                                                      │  数据分析   │
                                                      │(data_analyze)│
                                                      └────────────┘
```

---

## 三、核心决策节点详解

### 3.1 意图识别（Intent Recognition）

**文件位置**：`server/graph/nodes/intent.py`

**决策逻辑**：
```python
# LLM 输出结构化 JSON
{
    "intent": "data" | "chat" | "followup" | "clarify",
    "confidence": 0.0 ~ 1.0,
    "reason": "判断理由"
}

# 置信度决策规则
if confidence >= 0.8:
    → 直接采用该意图
elif 0.5 <= confidence < 0.8:
    → 结合用户记忆再判断
else:
    → clarify（反问澄清）
```

**Dify 工作流中的实现**（国际ChatBI-深度思考V3.0.yml）：
- 节点 ID：`1777346712277`
- 模型：DeepSeek-V3.1
- 输出：`problem_type`（1=数据分析，2=闲聊）+ `problem_alpha`（置信度）

---

### 3.2 条件路由（Conditional Edges）

**文件位置**：`server/graph/edges.py`

**路由函数矩阵**：

| 路由函数 | 输入状态 | 输出分支 | 触发条件 |
|---------|---------|---------|---------|
| `route_after_intent` | intent, confidence | chat/data/followup/clarify | 意图识别后 |
| `route_after_support` | bi_task | supported/unsupported | 支持性校验后 |
| `route_after_schema` | schema_context | found/not_found | Schema 检索后 |
| `route_after_sql_gen` | sql | success/error | SQL 生成后 |
| `route_after_guard` | guard_result | safe/repairable/malicious | 安全检查后 |
| `route_after_repair` | repair_count | retry/exceeded | SQL 修正后 |
| `route_after_exec` | query_result, sql_error | success/sql_error/fatal | SQL 执行后 |

---

### 3.3 四段式诊断 CoT（Reasoning Path）

**位置**：前端原型 index_v3_dynamic.html + 会议纪要.md

这是专为数据查询和经营诊断设计的**四段式诊断框架**：

```
[步骤一：解构 (Deconstruction)]
    AI自问："用户问'中东GS8库存异常'，
            '中东'对应什么大区字段？
            'GS8'对应什么车型？
            '库存异常'对应什么公式？
            我需要先调什么表结构 DDL 查字段？"
                              │
                              ▼
[步骤二：差距评估 (Gap Analysis)]
    AI自问："通过查表，我拿到当前中东GS8库存周转天数是65天。
            它与安全值30天的差距是多少？差距幅度达116%。"
                              │
                              ▼
[步骤三：归因诊断 (Attribution & Diagnosis)]
    AI自问："积压的根本原因是什么？
            是当地本月终端销量突然断崖式下跌，
            还是国内厂端到货太集中？
            我需要用SQL去查SC订单表和排产计划表来交叉定位因果。"
                              │
                              ▼
[步骤四：处方治理 (Prescription)]
    AI自问："因果定位了（到货太集中，超产20%）。
            那我该怎么去库？
            我应该调用知识库去检索历史上广汽海外GS8成功的去库存案例。
            整合并交付最终报告。"
```

---

### 3.4 SQL 自愈循环（Self-Healing Loop）

**决策流程**：
```
SQL 生成
    │
    ▼
┌─────────────┐
│  SQL 安全   │ ── malicious ──→ [FAIL]
│   门禁      │
└──────┬──────┘
        │ repairable
        ▼
┌─────────────┐
│  SQL 修正   │ ◄── 最多3次循环
│  (sql_repair)│
└──────┬──────┘
        │
        ├─ retry ──→ [SQL Guard] ──→ [SQL 执行]
        │
        └─ exceeded ──→ [FAIL]
```

**修正 Prompt 策略**：
```
Role: SQL Debugging Expert

Original User Question: {{#sys.query#}}
Incorrect SQL Query: {{#1750061504284.structured_output.sql#}}
上一个 SQL 执行报错信息：{{#1750061971446.error_message#}}
错误类型：{{#1750061971446.error_type#}}

请先仔细分析用户问题和上一个 SQL内容、报错信息、错误类型；
先分析错误的原因，一步一步设置优化计划后，再执行 SQL 修正。
```

---

### 3.5 ReAct 思维模式（Thought-Action-Observation）

**位置**：会议纪要.md §4.4-4.5

ChatBI 采用了**第三代 Reasoning Agent** 架构：

```
┌─────────────────────────────────────────────────────────┐
│                    ReAct 循环                            │
│                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────────┐    │
│   │  Thought │───▶│  Action   │───▶│ Observation  │    │
│   │  (思考)  │    │  (行动)   │    │   (观察)     │    │
│   └──────────┘    └──────────┘    └──────┬───────┘    │
│         ▲                                  │            │
│         └──────────────────────────────────┘            │
│                   循环收敛                               │
└─────────────────────────────────────────────────────────┘
```

**Thought 示例**：
- "用户问的是中东公司8月终端量，需要查询批发终端日表"
- "这个查询涉及同比计算，需要先查知识库看同环比指标的定义"

**Action 示例**：
- 调用 Dify 知识库检索
- 执行 SQL 查询
- 调用 ECharts 渲染

**Observation 示例**：
- 知识库返回："同环比计算需要用 DATE_SUB 或 DATE_FORMAT"
- SQL 执行返回：`[{country_name: "俄罗斯", terminal_qty: 1234}, ...]`

---

## 四、前端思维可视化（Live Thinking Stack）

**位置**：前端原型 index_v3_dynamic.html §思维链发光卡片

### 4.1 组件结构
```html
<div class="thinking-card">
    <div class="thinking-card-header">
        <h4>🤖 AI 思考中...</h4>
        <span class="toggle-icon">▼</span>
    </div>
    <div class="thinking-steps-container">
        <!-- 动态生成的思考步骤 -->
        <div class="thinking-step active|done|warning">
            <div class="step-icon-dot">1</div>
            <div class="step-body">
                <div class="step-title">意图识别</div>
                <div class="step-desc">正在分析您的需求...</div>
            </div>
        </div>
    </div>
</div>
```

### 4.2 步骤状态
| 状态 | CSS 类 | 视觉表现 |
|------|--------|---------|
| 进行中 | `.active` | 蓝色发光脉冲动画 |
| 已完成 | `.done` | 黑色实心圆 + 对勾 |
| 警告 | `.warning` | 橙色闪烁 + 感叹号 |

### 4.3 SQL Sandbox 调试卡片
```html
<div class="sql-sandbox">
    <div class="sql-sandbox-header">
        <span>🔧 SQL 执行日志</span>
        <i class="fa fa-copy"></i>
    </div>
    <pre>
-- Generated SQL
SELECT country_name, terminal_qty
FROM v_dm_sal_wolesale_terminal_dly
WHERE area_name = '中东公司'
  AND period_td BETWEEN '2024-08-01' AND '2024-08-31';

-- 执行结果: ✓ 成功 (23ms)
-- 返回行数: 5
    </pre>
</div>
```

---

## 五、技能（Skill）动态路由机制

**位置**：会议纪要.md §5.2 + Langraph/ 开发 Spec

### 5.1 Skill 定义规范
```python
from langchain_core.tools import tool

@tool
def gac_psi_analysis_skill(query: str, area_name: str) -> str:
    """
    【高阶专家技能：产销存(PSI)大盘经营诊断 Skill】

    当用户询问广汽乘用车海外的批发量、零售量、在店/在途库存天数、
    排产交付以及因库存超标导致的去库存问题时，
    你必须调用此技能进行诊断。

    :param query: 提取的具体问题（例如：分析GS8库存周转天数）
    :param area_name: 目标海外区域名称（例如：中东公司, 美洲大区, 亚洲大区）
    """
    # 技能内部的自决策微观逻辑：
    # 1. 自动从 local DB 提取该场景的 8 张表 DDL
    # 2. 依次并发发起 MCP StarRocks/MySQL 调用取数
    # 3. 将结果融合成 Markdown 交付
    return "产销存专家 Skill 跑数完毕..."
```

### 5.2 自动路由原理

**三步识别法**：

1. **解析文档 (Docstring Parsing)**
   - 大模型读取函数的 Docstring 和类型注解
   - 提取业务关键词：批发量、零售量、库存天数、排产交付

2. **绑定工具箱 (Tool Binding)**
   ```python
   skills = [
       gac_psi_analysis_skill,
       gac_finance_audit_skill,
       gac_competitor_analysis_skill
   ]
   model = ChatOpenAI(model="deepseek-chat").bind_tools(skills)
   ```

3. **大模型自主决策 (Autonomous Action Matching)**
   - 用户输入："帮我分析一下利比亚 Q1 的销量和库存是否有爆库风险？"
   - 大脑识别关键词：销量、库存、爆库 → 匹配 `gac_psi_analysis_skill`
   - 生成工具调用：`tool_calls: [{"name": "gac_psi_analysis_skill", "args": {"query": "Q1 销量和库存爆库风险", "area_name": "利比亚"}}]`

---

## 六、层级智能体架构（Hierarchical Agentic Architecture）

**位置**：会议纪要.md §4.7

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Agent（总大脑）                      │
│  职责：宏观步骤规划 + 任务路由分发                           │
│  工具：LangGraph 状态机编排                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ 任务分发
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Sub-Agent / Skills（高阶专家技能）              │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ PSI 专家    │  │ 财务审计    │  │ 竞品分析   │        │
│  │  Skill      │  │ Skill       │  │ Skill       │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                 │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Tools（最小原子物理工具层）                  │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ SQL Execute │  │ Vector      │  │ Web         │        │
│  │ (MySQL)     │  │ Retrieval   │  │ Search      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、关键文件索引

| 文件 | 作用 |
|------|------|
| `DIFY/国际ChatBI-深度思考V3.0.yml` | Dify 工作流配置（含意图识别、SQL生成、修正循环） |
| `Langraph/ChatBI_开发Spec_上.md` | LangGraph 状态机定义、条件路由函数 |
| `前端原型/index_v3_dynamic.html` | 前端思维可视化组件、SQL Sandbox |
| `docs/会议纪要.md` | 四段式诊断 CoT、ReAct 架构设计 |
| `server/graph/edges.py` | 7个条件路由函数实现 |
| `server/graph/nodes/*.py` | 各决策节点具体实现 |

---

## 八、总结

ChatBI 的 CoT 自主决策机制是一个**多层次、可视化、自纠错**的智能体系：

1. **层次分明**：从意图识别 → 任务构建 → SQL 执行 → 数据分析，层层递进
2. **条件路由**：7+ 个条件边实现真正的自决策（非线性分支）
3. **自我纠错**：SQL 修正循环最多3次，降低失败率
4. **思维可见**：前端实时展示思考步骤，增强用户信任
5. **技能编排**：通过 Docstring 实现 Skill 的动态绑定与自动路由
6. **ReAct 循环**：Thought → Action → Observation 持续收敛直到完成任务

这套机制让 AI 不是简单地按固定流程执行，而是能够根据中间结果动态调整下一步行动，真正实现了"自主决策"的能力。
