# CoT 自主决策核心概念速查卡

---

## 什么是 CoT？

**CoT (Chain of Thought)** = 分步骤逻辑演绎

> AI 不是靠直觉直接给答案，而是"写出解题步骤"，每一步文字成为下一步的"线索"。

---

## ChatBI CoT 四段式

| 步骤 | 名称 | 核心问题 |
|------|------|---------|
| 1 | 解构 (Deconstruction) | "用户问的是什么？涉及哪些字段/表？" |
| 2 | 差距评估 (Gap Analysis) | "当前值 vs 目标值差距多大？" |
| 3 | 归因诊断 (Attribution) | "根本原因是什么？" |
| 4 | 处方治理 (Prescription) | "怎么解决？调用什么 Skill？" |

---

## ReAct 三元素

| 元素 | 含义 | 在 ChatBI 中的体现 |
|------|------|-------------------|
| **Thought** | 思考 | "用户问的是库存问题，需要查库存表" |
| **Action** | 行动 | 调用 Dify 检索 / 执行 SQL |
| **Observation** | 观察 | 获取检索结果 / SQL 返回数据 |

---

## 意图识别三阈值

```
置信度 ≥ 0.8  → 直接采用
0.5 ≤ 置信度 < 0.8  → 结合记忆再判断
置信度 < 0.5  → 反问澄清
```

---

## SQL 安全三态

| 状态 | 含义 | 后续动作 |
|------|------|---------|
| `safe` | SQL 安全 | 直接执行 |
| `repairable` | 可修正 | 进入修正循环 |
| `malicious` | 恶意 | 阻断并失败 |

---

## SQL 修正循环

```
最多循环 3 次（MAX_SQL_REPAIR_COUNT=3）

SQL生成 → Guard判断 → [malicious] → FAIL
                    ↓
              [repairable] → SQL修正 → Guard判断
                    ↓               ↓
              [retry ≤ 3]    [exceeded] → FAIL
                    ↓
              [retry > 3] ──→ FAIL
                    ↓
                [safe] → 执行
```

---

## 条件路由速查

| 路由函数 | 输出分支数 |
|---------|-----------|
| `route_after_intent` | 4 (chat/data/followup/clarify) |
| `route_after_support` | 2 (supported/unsupported) |
| `route_after_schema` | 2 (found/not_found) |
| `route_after_guard` | 3 (safe/repairable/malicious) |
| `route_after_repair` | 2 (retry/exceeded) |
| `route_after_exec` | 3 (success/sql_error/fatal) |

---

## 前端思维栈状态

| CSS 类 | 状态 | 视觉 |
|--------|------|------|
| `.thinking-step.active` | 进行中 | 🔵 蓝色发光脉冲 |
| `.thinking-step.done` | 已完成 | ✅ 黑色对勾 |
| `.thinking-step.warning` | 警告 | ⚠️ 橙色闪烁 |

---

## Skill 动态路由三步

1. **Docstring 解析** — 提取业务关键词
2. **Tool Binding** — 绑定到 LLM
3. **自主匹配** — LLM 根据用户输入选择最合适的 Skill

---

## 关键文件路径

```
ChatBI_20260509/
├── Cot_research/                    # 本研究目录
│   ├── CoT自主决策机制研究报告.md
│   ├── CoT决策流程图解.md
│   ├── Dify与LangGraph实现对比.md
│   └── CoT核心概念速查卡.md        # 本文件
│
├── DIFY/
│   └── 国际ChatBI-深度思考V3.0.yml  # Dify 工作流
│
├── Langraph/
│   ├── ChatBI_开发Spec_上.md       # LangGraph 规格
│   └── ChatBI_开发Spec_下.md
│
├── server/graph/
│   ├── state.py                    # ChatBIState 定义
│   ├── builder.py                  # Graph 构建
│   ├── edges.py                    # 条件路由函数
│   └── nodes/                      # 各节点实现
│
└── 前端原型/
    └── index_v3_dynamic.html       # 思维可视化组件
```

---

*速查卡版本 v1.0 | 建议打印随身携带*
