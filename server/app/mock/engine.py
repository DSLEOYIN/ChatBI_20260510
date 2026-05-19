from __future__ import annotations

import asyncio
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from app.models.schemas import CanvasPayload, ChatResult, Intent, StreamEvent


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_intent(query: str, web_search: bool = False) -> Intent:
    q = query.lower()
    if web_search or any(k in q for k in ["最新", "新闻", "竞品", "促销", "网页", "舆情"]):
        return "search"
    if any(k in q for k in ["什么是", "定义", "口径", "怎么算", "解释"]):
        return "definition"
    if any(k in q for k in ["库存", "爆库", "库龄", "周转", "风险", "预警"]):
        return "alert"
    if any(k in q for k in ["对比", "排名", "同比", "环比", "比较"]):
        return "comparison"
    if any(k in q for k in ["分析", "诊断", "原因", "建议", "复盘"]):
        return "analysis"
    if any(k in q for k in ["销量", "终端", "批发", "订单", "排产", "目标", "达成", "gs8", "emzoom"]):
        return "simple_query"
    return "chat"


def build_sql(intent: Intent, query: str) -> str | None:
    if intent == "chat":
        return None
    if intent == "alert":
        return (
            "SELECT area_name, model_name, SUM(stock_qty) AS stock_qty, "
            "SUM(instore_qty) AS instore_qty, SUM(transit_qty) AS transit_qty, "
            "ROUND(SUM(stock_qty) / NULLIF(SUM(last_30d_terminal_qty), 0) * 30, 1) AS stock_days "
            "FROM v_dm_sal_stock_dly WHERE area_name = '中东公司' AND model_name = 'GS8' "
            "GROUP BY area_name, model_name;"
        )
    if intent == "definition":
        return None
    if intent == "search":
        return None
    return (
        "SELECT area_name, model_name, SUM(terminal_qty) AS terminal_qty, "
        "SUM(target_qty) AS target_qty, ROUND(SUM(terminal_qty) / NULLIF(SUM(target_qty), 0) * 100, 1) AS achievement_rate "
        "FROM v_dm_sal_wolesale_terminal_dly_v2 WHERE area_name = '中东公司' "
        "GROUP BY area_name, model_name ORDER BY terminal_qty DESC LIMIT 10;"
    )


def visible_steps(intent: Intent) -> list[dict]:
    base = [
        {"name": "问题理解", "status": "done", "detail": "识别用户问题中的区域、车型、指标和时间范围。"},
        {"name": "Skill 选择", "status": "done", "detail": skill_name(intent)},
    ]
    if intent == "chat":
        return base + [{"name": "直接回答", "status": "done", "detail": "无需查询业务数据，画布保持空白。"}]
    if intent == "definition":
        return base + [
            {"name": "知识库检索", "status": "done", "detail": "mock Dify Retrieve 召回指标口径。"},
            {"name": "画布装配", "status": "done", "detail": "生成指标定义卡。"},
        ]
    if intent == "search":
        return base + [
            {"name": "联网搜索", "status": "done", "detail": "mock Tavily Search 返回外部资讯结果。"},
            {"name": "画布装配", "status": "done", "detail": "生成搜索结果卡与引用来源。"},
        ]
    return base + [
        {"name": "SQL 生成", "status": "done", "detail": "生成只读 SELECT 查询，并默认折叠展示。"},
        {"name": "SQL 执行", "status": "done", "detail": "mock 查询返回经营样例数据。"},
        {"name": "数据解读", "status": "done", "detail": "生成用户可消费的结论和建议。"},
        {"name": "画布装配", "status": "done", "detail": "生成 KPI、图表、明细和建议组件。"},
    ]


def skill_name(intent: Intent) -> str:
    return {
        "chat": "闲聊 Skill",
        "simple_query": "数据查询 Skill",
        "analysis": "数据分析 Skill",
        "comparison": "对比分析 Skill",
        "alert": "库存预警 Skill",
        "definition": "知识库检索 Skill",
        "search": "联网搜索 Skill",
    }[intent]


def build_answer(intent: Intent) -> str:
    if intent == "chat":
        return "我在。你可以直接问销量、库存、订单、排产和目标达成，也可以让我解释指标口径。"
    if intent == "alert":
        return "中东公司 GS8 当前库存周转天数约 65 天，高于 45 天健康线，存在阶段性爆库风险。主要压力来自在店库存偏高和近 30 天终端动销放缓，建议优先做高库龄车辆清理与重点国家促销联动。"
    if intent == "definition":
        return "库存周转天数用于衡量当前库存可支撑销售的天数，通常按库存量除以近 30 天日均终端销量计算。该指标越高，说明库存消化压力越大。"
    if intent == "search":
        return "已整理 mock 联网搜索结果：近期中东 SUV 市场促销活跃，竞品优惠集中在金融贴息、置换补贴和保养礼包，建议后续结合内部库存压力判断是否跟进。"
    if intent == "comparison":
        return "从 mock 数据看，GS8 终端量低于 EMZOOM，但库存周转天数显著更高，资源应优先投向 GS8 去库存，同时保持 EMZOOM 供给稳定。"
    if intent == "analysis":
        return "中东公司本月销量达成率约 91.6%，核心缺口集中在 GS8 与 EMKOO。建议把诊断重点放在库存结构、终端线索转化和国家间资源调拨。"
    return "中东公司本月 mock 终端销量 4,860 台，目标达成率 91.6%。GS8 库存偏高但 EMZOOM 动销表现较好。"


def build_canvas(intent: Intent) -> CanvasPayload:
    if intent == "chat":
        return CanvasPayload(
            title="闲聊模式",
            subtitle="当前问题无需查询业务数据",
            intent=intent,
            components=[
                {
                    "id": "chat-answer",
                    "type": "answer",
                    "title": "回答",
                    "props": {"content": build_answer(intent)},
                }
            ],
        )
    if intent == "definition":
        return CanvasPayload(
            title="指标定义",
            subtitle="来自 mock 知识库检索",
            intent=intent,
            components=[
                {
                    "id": "final-answer",
                    "type": "answer",
                    "title": "最终回答",
                    "props": {"content": build_answer(intent)},
                },
                {
                    "id": "def-stock-days",
                    "type": "definition",
                    "title": "库存周转天数",
                    "props": {
                        "definition": "当前库存可支撑销售的预计天数。",
                        "formula": "库存周转天数 = 当前库存 / 近30天日均终端销量",
                        "note": "通常 30-45 天为健康区间，超过 60 天需要重点预警。",
                    },
                }
            ],
        )
    if intent == "search":
        return CanvasPayload(
            title="联网搜索结果",
            subtitle="mock Tavily Search 结果",
            intent=intent,
            components=[
                {
                    "id": "final-answer",
                    "type": "answer",
                    "title": "最终回答",
                    "props": {"content": build_answer(intent)},
                },
                {
                    "id": "search-results",
                    "type": "search_results",
                    "title": "外部市场信息",
                    "props": {
                        "items": [
                            {"title": "中东 SUV 市场促销力度提升", "source": "Mock News", "summary": "多品牌集中推出金融贴息与置换补贴。"},
                            {"title": "竞品七座 SUV 强化保养礼包", "source": "Mock Auto", "summary": "售后权益成为高配车型成交拉动项。"},
                        ]
                    },
                }
            ],
        )
    components = [
        {
            "id": "final-answer",
            "type": "answer",
            "title": "最终回答",
            "props": {"content": build_answer(intent)},
        },
        {
            "id": "kpi-grid",
            "type": "kpi_grid",
            "title": "关键指标",
            "props": {
                "items": [
                    {"label": "终端销量", "value": "4,860", "unit": "台", "trend": "+8.2%"},
                    {"label": "目标达成率", "value": "91.6", "unit": "%", "trend": "-3.4pp"},
                    {"label": "GS8库存", "value": "1,280", "unit": "台", "trend": "+18.5%"},
                    {"label": "周转天数", "value": "65", "unit": "天", "trend": "高风险"},
                ]
            },
        },
        {
            "id": "trend-chart",
            "type": "chart",
            "title": "近 6 周终端销量趋势",
            "props": {
                "option": {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": 36, "right": 16, "top": 24, "bottom": 28},
                    "xAxis": {"type": "category", "data": ["W1", "W2", "W3", "W4", "W5", "W6"]},
                    "yAxis": {"type": "value"},
                    "series": [{"name": "终端销量", "type": "line", "smooth": True, "data": [720, 810, 790, 860, 835, 845]}],
                }
            },
        },
        {
            "id": "detail-table",
            "type": "table",
            "title": "车型明细",
            "props": {
                "download": "/api/downloads/mock-detail.csv",
                "columns": ["车型", "终端销量", "目标", "达成率", "库存"],
                "rows": [
                    ["GS8", "920", "1,180", "78.0%", "1,280"],
                    ["EMZOOM", "1,560", "1,420", "109.9%", "580"],
                    ["EMKOO", "1,120", "1,300", "86.2%", "740"],
                    ["EMPOW", "1,260", "1,405", "89.7%", "690"],
                ],
            },
        },
        {
            "id": "insight",
            "type": "insight",
            "title": "结论与建议",
            "props": {
                "items": [
                    "GS8 去库存优先级最高，建议聚焦沙特和阿联酋高库龄车辆。",
                    "EMZOOM 动销健康，需防止旺季断货。",
                    "目标差距主要来自高价车型转化不足，可联动金融方案提升成交。",
                ]
            },
        },
    ]
    if intent == "alert":
        components.insert(
            0,
            {
                "id": "risk",
                "type": "risk",
                "title": "库存风险预警",
                "props": {"level": "高风险", "value": "65天", "threshold": "45天", "summary": "GS8 库存周转天数超健康线 20 天。"},
            },
        )
    return CanvasPayload(
        title="预警详情" if intent == "alert" else "业务答案画布",
        subtitle="由 mock Agent 最终产物动态装配",
        intent=intent,
        components=components,
    )


def build_result(request, conversation_id: str) -> ChatResult:
    intent = detect_intent(request.content, request.web_search)
    return ChatResult(
        conversation_id=conversation_id,
        intent=intent,
        answer=build_answer(intent),
        visible_steps=visible_steps(intent),
        sql=build_sql(intent, request.content),
        canvas=build_canvas(intent),
    )


async def stream_result(result: ChatResult) -> AsyncIterator[StreamEvent]:
    yield StreamEvent(type="conversation_id", data=result.conversation_id)
    for step in result.visible_steps:
        yield StreamEvent(type="step", data=step)
        await asyncio.sleep(0.25)
    if result.sql:
        yield StreamEvent(type="sql", data=result.sql)
        await asyncio.sleep(0.15)
    yield StreamEvent(type="answer", data=result.answer)
    await asyncio.sleep(0.15)
    yield StreamEvent(type="canvas", data=result.canvas.model_dump())
    yield StreamEvent(type="done", data=None)


def make_conversation(user_id: str, title: str = "新对话") -> dict:
    ts = now_iso()
    return {"id": str(uuid.uuid4()), "user_id": user_id, "title": title, "created_at": ts, "updated_at": ts, "messages": []}


def detail_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["车型", "终端销量", "目标", "达成率", "库存"])
    writer.writerows([
        ["GS8", "920", "1180", "78.0%", "1280"],
        ["EMZOOM", "1560", "1420", "109.9%", "580"],
        ["EMKOO", "1120", "1300", "86.2%", "740"],
        ["EMPOW", "1260", "1405", "89.7%", "690"],
    ])
    return output.getvalue()
