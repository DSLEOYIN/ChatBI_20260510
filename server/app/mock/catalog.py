CANVAS_PAYLOAD_SCHEMA = {
    "version": "2026-05-21.mock.v1",
    "description": "业务画布由结构化 JSON 组件驱动，前端按 type 渲染。",
    "payload": {
        "title": "画布标题",
        "subtitle": "画布副标题或流式回答摘要",
        "intent": "chat | simple_query | analysis | comparison | alert | definition | search",
        "components": "CanvasComponent[]",
    },
    "component_types": {
        "answer": {"required_props": ["content"], "usage": "最终业务回答。"},
        "kpi": {"required_props": ["label", "value"], "optional_props": ["unit", "trend", "status"], "usage": "单指标卡。"},
        "kpi_grid": {"required_props": ["items"], "usage": "多指标 KPI 网格，items 内字段同 kpi。"},
        "chart": {"required_props": ["option"], "usage": "ECharts option。"},
        "table": {"required_props": ["columns", "rows"], "optional_props": ["download"], "usage": "明细表和下载入口。"},
        "risk": {"required_props": ["level", "value", "threshold", "summary"], "usage": "风险预警卡。"},
        "definition": {"required_props": ["definition", "formula"], "optional_props": ["note"], "usage": "指标口径卡。"},
        "search_results": {"required_props": ["items"], "usage": "外部搜索结果与引用来源。"},
        "insight": {"required_props": ["items"], "usage": "结论、原因和建议。"},
    },
}

DOWNLOAD_CONTRACT = {
    "version": "2026-05-21.mock.v1",
    "format": "csv",
    "endpoint": "/api/downloads/mock-detail.csv",
    "filename": "chatbi_mock_detail.csv",
    "content_type": "text/csv; charset=utf-8",
    "note": "第一阶段明确继续使用 CSV，前端文案统一为“下载 CSV 明细”。后续可平滑新增 xlsx endpoint。",
}

STREAM_EVENT_CONTRACT = {
    "version": "2026-05-22.mock.v1",
    "endpoint": "/api/chat/stream",
    "transport": "server-sent-events",
    "content_type": "text/event-stream",
    "wire_format": {
        "event": "same value as data.type",
        "data": {
            "type": "conversation_id | step | sql | answer | canvas | done | error",
            "sequence": "monotonic integer starting at 1 within one stream",
            "emitted_at": "ISO-8601 UTC timestamp",
            "data": "event-specific payload",
        },
    },
    "events": {
        "conversation_id": {"order": 1, "data": "string conversation id", "required": True},
        "step": {
            "order": "2..n",
            "data": "ExecutionStep",
            "required": True,
            "schema": {
                "name": "string",
                "status": "done | warning | error",
                "detail": "string",
                "tool": "string | null",
                "duration": "string | null",
                "input": "object",
                "output": "object",
            },
        },
        "sql": {"order": "after step events when sql exists", "data": "string readonly SQL", "required": False},
        "answer": {"order": "after sql or after step events", "data": "string final business answer", "required": True},
        "canvas": {
            "order": "after answer",
            "data": "CanvasPayload",
            "required": True,
            "component_types": ["answer", "kpi", "kpi_grid", "chart", "table", "risk", "definition", "search_results", "insight"],
        },
        "done": {"order": "last successful event", "data": None, "required": True},
        "error": {"order": "terminal failure event", "data": {"message": "string"}, "required": False},
    },
}

MOCK_API_CONTRACT = {
    "version": "2026-05-22.mock.v1",
    "phase": "phase-1-react-fastapi-mock",
    "capabilities": {
        "conversation_create": {"method": "POST", "path": "/api/conversations"},
        "conversation_list": {"method": "GET", "path": "/api/conversations"},
        "conversation_detail": {"method": "GET", "path": "/api/conversations/{conversation_id}"},
        "conversation_delete": {"method": "DELETE", "path": "/api/conversations/{conversation_id}"},
        "conversation_pin": {"method": "POST", "path": "/api/conversations/{conversation_id}/pin"},
        "chat": {"method": "POST", "path": "/api/chat"},
        "chat_stream": {"method": "POST", "path": "/api/chat/stream"},
        "data_assets": {
            "method": "GET",
            "path": "/api/config/data-assets",
            "source": "server/config/data_assets.json",
            "override_env": "CHATBI_DATA_ASSETS_PATH",
        },
        "skills": {"method": "GET", "path": "/api/config/skills"},
        "canvas_schema": {"method": "GET", "path": "/api/config/canvas-schema"},
        "stream_contract": {"method": "GET", "path": "/api/config/stream-contract"},
        "download_contract": {"method": "GET", "path": "/api/config/download-contract"},
        "storage_status": {"method": "GET", "path": "/api/config/storage"},
        "mock_search": {"method": "GET", "path": "/api/mock/search"},
        "knowledge_retrieve": {
            "method": "POST",
            "path": "/api/knowledge/retrieve",
            "provider": "mock-dify by default; real Dify when CHATBI_DIFY_ENABLED=true",
        },
        "dify_status": {"method": "GET", "path": "/api/config/dify"},
        "detail_download": {"method": "GET", "path": "/api/downloads/mock-detail.csv", "format": "csv"},
    },
    "intents": ["chat", "simple_query", "analysis", "comparison", "alert", "definition", "search"],
    "canvas_component_types": ["answer", "kpi", "kpi_grid", "chart", "table", "risk", "definition", "search_results", "insight"],
    "download_format": "csv",
}

DIFY_DATASETS = {
    "9e07fcf2-56cf-4f2c-b115-8727e721fbd3": {
        "name": "车型知识库",
        "description": "包含车型参数、配置、功能介绍等车型相关文档。",
        "use_cases": ["车型配置", "参数对比", "功能介绍"],
    },
    "486476a8-15f6-4359-bcb5-6efd40d90373": {
        "name": "国际-大区知识库",
        "description": "国际大区相关资料，适合跨区域经营问题。",
        "use_cases": ["大区信息", "跨大区业务"],
    },
    "90560d64-db69-4c66-88ca-9c86a340dd5d": {
        "name": "国际-国家知识库",
        "description": "国家级市场、政策和法规资料。",
        "use_cases": ["国家政策", "市场数据", "法规要求"],
    },
    "ffa84ba6-4ec9-44a0-8f6d-594b27f7a829": {
        "name": "国际问答对-V3",
        "description": "默认高质量问答库，适合通用业务咨询。",
        "use_cases": ["通用问答", "常见问题", "业务咨询"],
    },
    "959f346f-f950-480c-a1d7-d792ad10be33": {
        "name": "同环比-国际问答对-V2",
        "description": "历史同比、环比和同期对比资料。",
        "use_cases": ["同比", "环比", "历史对比"],
    },
}

DIFY_DATASET_ALIASES = {info["name"]: dataset_id for dataset_id, info in DIFY_DATASETS.items()}

MOCK_DIFY_RECORDS = [
    {
        "segment_id": "mock-dify-stock-days",
        "document_name": "库存指标口径说明",
        "content": "库存周转天数 = 当前库存 / 近30天日均终端销量。通常 30-45 天为健康区间，超过 60 天需要重点预警。",
        "score": 0.92,
        "metadata": {"source": "mock", "metric": "stock_days"},
    },
    {
        "segment_id": "mock-dify-achievement-rate",
        "document_name": "目标达成率指标说明",
        "content": "目标达成率 = 实际销量 / 目标销量 * 100%。低于 90% 时需要关注缺口来源和资源投放节奏。",
        "score": 0.86,
        "metadata": {"source": "mock", "metric": "achievement_rate"},
    },
    {
        "segment_id": "mock-dify-inventory-warning",
        "document_name": "库存预警业务规则",
        "content": "库存预警需要结合总库存、在店库存、在途库存、库龄结构和近 30 天终端动销综合判断。",
        "score": 0.81,
        "metadata": {"source": "mock", "domain": "inventory"},
    },
]

MOCK_SEARCH_RESULTS = {
    "query": "中东 SUV 市场 竞品 促销",
    "provider": "mock-tavily",
    "search_depth": "advanced",
    "include_answer": True,
    "answer": "近期中东 SUV 市场促销活跃，竞品优惠集中在金融贴息、置换补贴和保养礼包。",
    "results": [
        {
            "title": "中东 SUV 市场促销力度提升",
            "url": "https://mock.example.com/middle-east-suv-promotion",
            "source": "Mock News",
            "published_at": "2026-05-18",
            "summary": "多品牌集中推出金融贴息与置换补贴，七座 SUV 竞争热度提升。",
            "score": 0.92,
        },
        {
            "title": "竞品七座 SUV 强化保养礼包",
            "url": "https://mock.example.com/seven-seat-suv-service-package",
            "source": "Mock Auto",
            "published_at": "2026-05-16",
            "summary": "售后权益成为高配车型成交拉动项，部分车型叠加延保权益。",
            "score": 0.87,
        },
    ],
    "fallback": {
        "strategy": "external_search_unavailable",
        "message": "联网搜索不可用时，保留内部经营数据分析，并在画布提示外部来源未更新。",
    },
}

SKILLS = [
    {
        "id": "sales_analysis",
        "name": "销售分析 Skill",
        "scenario": "销量、批发、终端、目标达成、车型排名和趋势分析。",
        "triggers": ["销量", "终端", "批发", "目标", "达成", "排名", "同比", "环比"],
        "trigger_conditions": ["问题包含销售指标", "需要按区域/国家/车型聚合", "不需要外部实时网页信息"],
        "inputs": {
            "query": "用户自然语言问题",
            "entities": ["area_name", "country_name", "model_name", "period"],
            "constraints": ["readonly_sql", "allowed_tables"],
        },
        "outputs": {
            "answer": "业务结论",
            "sql": "只读 SELECT",
            "canvas_components": ["answer", "kpi_grid", "chart", "table", "insight"],
        },
        "mcp_tools": [
            {"name": "mock-metadata", "purpose": "读取表字段、别名和指标口径。"},
            {"name": "mock-mysql-query", "purpose": "执行 mock 只读查询。"},
        ],
        "tools": ["mock-metadata", "mock-mysql-query"],
        "output": "answer + kpi_grid + chart + table + insight",
        "fallback_strategy": "SQL 生成或查询失败时，返回可解释的失败节点，并给出建议改问方式。",
    },
    {
        "id": "inventory_alert",
        "name": "库存预警 Skill",
        "scenario": "库存、爆库、库龄、在途、在店库存和周转天数风险诊断。",
        "triggers": ["库存", "爆库", "库龄", "周转", "在途", "安全线", "风险"],
        "trigger_conditions": ["问题包含库存健康度或异常诊断", "需要结合终端销量计算库存周转"],
        "inputs": {
            "query": "用户自然语言问题",
            "entities": ["area_name", "model_name", "period"],
            "metrics": ["stock_qty", "instore_qty", "transit_qty", "stock_days"],
        },
        "outputs": {
            "answer": "风险结论和去库存建议",
            "sql": "库存与近 30 天终端销量查询",
            "canvas_components": ["risk", "answer", "kpi_grid", "chart", "table", "insight"],
        },
        "mcp_tools": [
            {"name": "mock-metadata", "purpose": "读取库存口径、健康线和字段别名。"},
            {"name": "mock-mysql-query", "purpose": "执行库存 mock 查询。"},
            {"name": "sql-repair-skill", "purpose": "字段歧义或口径缺失时自动修复 SQL。"},
        ],
        "tools": ["mock-metadata", "mock-mysql-query", "sql-repair-skill"],
        "output": "risk + answer + kpi_grid + chart + table + insight",
        "fallback_strategy": "库存口径缺失时返回风险无法判定说明，并展示已可用的库存基础数。",
    },
    {
        "id": "metric_definition",
        "name": "指标口径 Skill",
        "scenario": "解释指标定义、计算公式、健康线和业务使用方式。",
        "triggers": ["什么是", "定义", "口径", "怎么算", "计算公式"],
        "trigger_conditions": ["问题重点是概念解释", "无需执行经营数据查询"],
        "inputs": {"query": "用户自然语言问题", "keywords": ["指标名", "业务别名"]},
        "outputs": {"answer": "指标解释", "canvas_components": ["answer", "definition"]},
        "mcp_tools": [{"name": "mock-dify-retrieve", "purpose": "召回 Dify 知识库中的指标口径。"}],
        "tools": ["mock-dify-retrieve"],
        "output": "answer + definition",
        "fallback_strategy": "知识库无命中时返回通用解释，并提示需维护指标口径。",
    },
    {
        "id": "web_search",
        "name": "联网搜索 Skill",
        "scenario": "最新资讯、竞品促销、网页舆情和外部市场信息。",
        "triggers": ["最新", "新闻", "竞品", "促销", "网页", "舆情"],
        "trigger_conditions": ["用户打开联网搜索", "问题包含外部实时信息诉求"],
        "inputs": {"query": "搜索关键词", "search_depth": "basic | advanced", "include_answer": True},
        "outputs": {"answer": "搜索摘要", "canvas_components": ["answer", "search_results"]},
        "mcp_tools": [{"name": "tavily-search.search_web", "purpose": "搜索网页并返回引用来源。"}],
        "tools": ["tavily-search.search_web"],
        "output": "answer + search_results",
        "fallback_strategy": "Tavily 不可用时展示 mock 固定结果或提示联网搜索暂不可用。",
    },
]

DATA_ASSETS = [
    {
        "table": "v_dm_sal_wolesale_terminal_dly",
        "name": "批发终端日表",
        "domain": "经营域",
        "description": "批发量、终端量、区域/国家/车型分析。",
        "aliases": ["销量表", "终端销量", "批发终端", "经营日报"],
        "metric_paths": ["终端销量", "批发量", "目标达成率"],
        "fields": [
            {"name": "area_name", "chinese_name": "区域名称", "type": "dimension", "example": "中东公司", "aliases": ["大区", "子公司"]},
            {"name": "country_name", "chinese_name": "国家", "type": "dimension", "example": "沙特", "aliases": ["市场"]},
            {"name": "model_name", "chinese_name": "车型名称", "type": "dimension", "example": "GS8", "aliases": ["车型"]},
            {"name": "terminal_qty", "chinese_name": "终端销量", "type": "metric", "example": 920, "aliases": ["零售", "终端"]},
            {"name": "wholesale_qty", "chinese_name": "批发量", "type": "metric", "example": 1040, "aliases": ["批售"]},
        ],
    },
    {
        "table": "v_dm_sal_wolesale_terminal_dly_v2",
        "name": "批发终端预实表",
        "domain": "经营域",
        "description": "批发/终端实际与计划，用于达成率和目标差距分析。",
        "aliases": ["预实表", "目标达成", "销量计划"],
        "metric_paths": ["目标达成率", "销量缺口", "计划完成率"],
        "fields": [
            {"name": "area_name", "chinese_name": "区域名称", "type": "dimension", "example": "中东公司", "aliases": ["大区"]},
            {"name": "model_name", "chinese_name": "车型名称", "type": "dimension", "example": "EMZOOM", "aliases": ["车型"]},
            {"name": "terminal_qty", "chinese_name": "终端实际", "type": "metric", "example": 1560, "aliases": ["实际销量"]},
            {"name": "target_qty", "chinese_name": "目标", "type": "metric", "example": 1420, "aliases": ["计划", "销量目标"]},
            {"name": "achievement_rate", "chinese_name": "达成率", "type": "derived", "example": "109.9%", "aliases": ["完成率"]},
        ],
    },
    {
        "table": "v_dm_sal_sc_order_dly",
        "name": "SC 订单日表",
        "domain": "销售域",
        "description": "新增订单、区域/国家/车型订单分析。",
        "aliases": ["订单表", "SC订单", "新增订单"],
        "metric_paths": ["新增订单", "订单转化", "订单趋势"],
        "fields": [
            {"name": "order_qty", "chinese_name": "新增订单", "type": "metric", "example": 438, "aliases": ["订单数"]},
            {"name": "model_name", "chinese_name": "车型名称", "type": "dimension", "example": "GS8", "aliases": ["车型"]},
            {"name": "country_name", "chinese_name": "国家", "type": "dimension", "example": "阿联酋", "aliases": ["市场"]},
        ],
    },
    {
        "table": "v_dm_sal_sc_order_dly_v2",
        "name": "SC 订单预实表",
        "domain": "销售域",
        "description": "订单实际与计划，用于订单目标达成分析。",
        "aliases": ["订单预实", "订单计划"],
        "metric_paths": ["订单达成率", "订单缺口"],
        "fields": [
            {"name": "order_qty", "chinese_name": "订单实际", "type": "metric", "example": 438, "aliases": ["实际订单"]},
            {"name": "target_order_qty", "chinese_name": "订单目标", "type": "metric", "example": 520, "aliases": ["计划订单"]},
        ],
    },
    {
        "table": "v_dm_sal_stock_dly",
        "name": "库存日表",
        "domain": "库存域",
        "description": "总库存、在途、在店、子公司库存、厂端库存、库龄。",
        "aliases": ["库存表", "库龄表", "在途库存", "在店库存"],
        "metric_paths": ["总库存", "库存周转天数", "库龄结构", "爆库风险"],
        "fields": [
            {"name": "area_name", "chinese_name": "区域名称", "type": "dimension", "example": "中东公司", "aliases": ["大区"]},
            {"name": "model_name", "chinese_name": "车型名称", "type": "dimension", "example": "GS8", "aliases": ["车型"]},
            {"name": "stock_qty", "chinese_name": "总库存", "type": "metric", "example": 1280, "aliases": ["库存"]},
            {"name": "instore_qty", "chinese_name": "在店库存", "type": "metric", "example": 940, "aliases": ["店端库存"]},
            {"name": "transit_qty", "chinese_name": "在途库存", "type": "metric", "example": 340, "aliases": ["经销商在途"]},
            {"name": "stock_days", "chinese_name": "库存周转天数", "type": "derived", "example": 65, "aliases": ["周转", "库存天数"]},
        ],
    },
    {
        "table": "v_dm_sal_remain_order_dly",
        "name": "剩余订单日表",
        "domain": "销售域",
        "description": "剩余订单、配车、未配车、超时预警。",
        "aliases": ["剩余订单", "未交订单", "订单池"],
        "metric_paths": ["剩余订单", "未配车订单", "超时订单"],
        "fields": [
            {"name": "remain_order_qty", "chinese_name": "剩余订单", "type": "metric", "example": 126, "aliases": ["待交订单"]},
            {"name": "allocated_qty", "chinese_name": "已配车", "type": "metric", "example": 88, "aliases": ["配车"]},
            {"name": "timeout_qty", "chinese_name": "超时订单", "type": "metric", "example": 9, "aliases": ["逾期"]},
        ],
    },
    {
        "table": "v_dm_sal_scheduling_dly",
        "name": "排产日表",
        "domain": "物流域",
        "description": "交付量、下线量、排产执行。",
        "aliases": ["排产", "到货", "发运", "物流"],
        "metric_paths": ["下线量", "交付量", "到货差额"],
        "fields": [
            {"name": "offline_qty", "chinese_name": "下线量", "type": "metric", "example": 610, "aliases": ["生产下线"]},
            {"name": "delivery_qty", "chinese_name": "交付量", "type": "metric", "example": 540, "aliases": ["到货"]},
            {"name": "plan_qty", "chinese_name": "排产计划", "type": "metric", "example": 680, "aliases": ["计划"]},
        ],
    },
    {
        "table": "v_dm_sal_scheduling_dly_v2",
        "name": "排产预实表",
        "domain": "物流域",
        "description": "下线实际与计划，用于排产执行和到货缺口分析。",
        "aliases": ["排产预实", "生产计划"],
        "metric_paths": ["排产达成率", "排产缺口"],
        "fields": [
            {"name": "offline_qty", "chinese_name": "下线实际", "type": "metric", "example": 610, "aliases": ["实际下线"]},
            {"name": "plan_offline_qty", "chinese_name": "下线计划", "type": "metric", "example": 680, "aliases": ["计划下线"]},
        ],
    },
]

METRIC_DEFINITIONS = [
    {
        "id": "stock_days",
        "name": "库存周转天数",
        "aliases": ["库存天数", "周转天数", "库存周转"],
        "formula": "库存周转天数 = 当前库存 / 近30天日均终端销量",
        "healthy_range": "30-45 天",
        "warning_rule": "超过 60 天标记为高风险。",
        "source_tables": ["v_dm_sal_stock_dly", "v_dm_sal_wolesale_terminal_dly"],
    },
    {
        "id": "achievement_rate",
        "name": "目标达成率",
        "aliases": ["完成率", "达成"],
        "formula": "目标达成率 = 实际销量 / 目标销量 * 100%",
        "healthy_range": ">= 100%",
        "warning_rule": "低于 90% 需要关注缺口来源。",
        "source_tables": ["v_dm_sal_wolesale_terminal_dly_v2"],
    },
]
