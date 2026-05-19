SKILLS = [
    {
        "id": "sales_analysis",
        "name": "销售分析 Skill",
        "triggers": ["销量", "终端", "批发", "目标", "达成"],
        "tools": ["mock-mysql-query", "mock-metadata"],
        "output": "kpi_grid + chart + table + insight",
    },
    {
        "id": "inventory_alert",
        "name": "库存预警 Skill",
        "triggers": ["库存", "爆库", "库龄", "周转", "在途"],
        "tools": ["mock-mysql-query", "mock-metadata"],
        "output": "risk_card + kpi_grid + trend_chart + recommendation",
    },
    {
        "id": "metric_definition",
        "name": "指标口径 Skill",
        "triggers": ["什么是", "定义", "口径", "怎么算"],
        "tools": ["mock-dify-retrieve"],
        "output": "definition_card",
    },
    {
        "id": "web_search",
        "name": "联网搜索 Skill",
        "triggers": ["最新", "新闻", "竞品", "促销", "网页", "舆情"],
        "tools": ["tavily-search.search_web"],
        "output": "search_result_cards",
    },
]

DATA_ASSETS = [
    {
        "table": "v_dm_sal_wolesale_terminal_dly",
        "name": "批发终端日表",
        "usage": "批发量、终端量、区域/国家/车型分析",
    },
    {
        "table": "v_dm_sal_sc_order_dly",
        "name": "SC 订单日表",
        "usage": "新增订单、区域/国家/车型订单分析",
    },
    {
        "table": "v_dm_sal_stock_dly",
        "name": "库存日表",
        "usage": "总库存、在途、在店、子公司库存、厂端库存、库龄",
    },
    {
        "table": "v_dm_sal_remain_order_dly",
        "name": "剩余订单日表",
        "usage": "剩余订单、配车、未配车、超时预警",
    },
    {
        "table": "v_dm_sal_scheduling_dly",
        "name": "排产日表",
        "usage": "交付量、下线量、排产执行",
    },
]
