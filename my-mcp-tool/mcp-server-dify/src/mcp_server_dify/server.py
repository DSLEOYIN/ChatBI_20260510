import argparse
import asyncio
import os
import sys
import httpx
from typing import Annotated, Optional
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent
from loguru import logger

logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

mcp = FastMCP('mcp-server-dify')

# Configuration
DIFY_API_BASE_URL = os.getenv("DIFY_API_BASE_URL", "http://10.30.11.215:9879")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "dataset-S5L6smkj8ovnSz8rMl5DZUvj")

HEADERS = {
    "Authorization": f"Bearer {DIFY_API_KEY}",
    "Content-Type": "application/json"
}

# Predefined dataset mapping with descriptions
DATASETS = {
    "9e07fcf2-56cf-4f2c-b115-8727e721fbd3": {
        "name": "车型知识库",
        "description": "包含车型相关文档，如车型参数、配置、特性等",
        "use_cases": ["询问车型配置", "车型参数对比", "车型功能介绍"]
    },
    "486476a8-15f6-4359-bcb5-6efd40d90373": {
        "name": "国际-大区知识库",
        "description": "国际大区相关数据，如亚太区、欧洲区等",
        "use_cases": ["大区信息查询", "跨大区业务问题"]
    },
    "90560d64-db69-4c66-88ca-9c86a340dd5d": {
        "name": "国际-国家知识库",
        "description": "国家级数据，包含各个国家的特定信息",
        "use_cases": ["国家政策查询", "国家市场数据", "国家法规要求"]
    },
    "ffa84ba6-4ec9-44a0-8f6d-594b27f7a829": {
        "name": "国际问答对-V3",
        "description": "当前默认测试的高质量问答库，包含各类常见问题及答案",
        "use_cases": ["通用问答", "常见问题解答", "业务咨询"]
    },
    "959f346f-f950-480c-a1d7-d792ad10be33": {
        "name": "同环比-国际问答对-V2",
        "description": "历史版本数据，主要用于同比环比相关问题",
        "use_cases": ["同期对比", "环比分析", "历史数据查询"]
    },
}

# Aliases for easy access by name
DATASET_ALIASES = {
    "车型知识库": "9e07fcf2-56cf-4f2c-b115-8727e721fbd3",
    "国际-大区知识库": "486476a8-15f6-4359-bcb5-6efd40d90373",
    "国际-国家知识库": "90560d64-db69-4c66-88ca-9c86a340dd5d",
    "国际问答对-V3": "ffa84ba6-4ec9-44a0-8f6d-594b27f7a829",
    "同环比-国际问答对-V2": "959f346f-f950-480c-a1d7-d792ad10be33",
}

# Legacy compatibility
DATASET_MAPPING = DATASET_ALIASES


def get_dataset_id(name_or_id: str) -> str:
    """Resolve dataset name to ID, or return as-is if already an ID."""
    if name_or_id in DATASET_ALIASES:
        return DATASET_ALIASES[name_or_id]
    if name_or_id in DATASETS:
        return name_or_id
    return name_or_id


def get_dataset_info_by_id(ds_id: str) -> dict:
    """Get dataset info by ID."""
    return DATASETS.get(ds_id, {"name": ds_id, "description": "未知描述", "use_cases": []})


async def dify_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make async request to DIFY API."""
    url = f"{DIFY_API_BASE_URL}{endpoint}"
    timeout = kwargs.pop("timeout", 30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(method, url, headers=HEADERS, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text}
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {"error": str(e)}


@mcp.tool(description="从DIFY知识库检索片段。支持纯语义检索、纯关键词检索和混合检索三种模式。")
async def retrieve_segments(
    query: Annotated[str, Field(description="用户输入的检索词")],
    dataset_id: Annotated[str, Field(description="知识库ID或名称（如：车型知识库、国际-大区知识库、国际-国家知识库、国际问答对-V3、同环比-国际问答对-V2）")],
    search_method: Annotated[str, Field(description="检索策略: semantic_search(语义检索), keyword_search(关键词检索), hybrid_search(混合检索)")] = "semantic_search",
    top_k: Annotated[int, Field(description="召回结果的最大数量（1~20）")] = 3,
    score_threshold_enabled: Annotated[bool, Field(description="是否开启分数阈值过滤")] = False,
    score_threshold: Annotated[float, Field(description="分数阈值（0~1），仅在score_threshold_enabled=true时生效")] = 0.5,
    reranking_enable: Annotated[bool, Field(description="是否开启Rerank大模型重排")] = False,
    reranking_provider_name: Annotated[str, Field(description="Rerank模型提供商名称")] = "langgenius/siliconflow/siliconflow",
    reranking_model_name: Annotated[str, Field(description="Rerank模型名称")] = "netease-youdao/bce-reranker-base_v1",
    vector_weight: Annotated[float, Field(description="混合检索中语义权重（0~1），关键词权重自动设为1-vector_weight")] = 0.7,
) -> ToolResult:
    """
    从DIFY知识库检索相关片段。

    支持三种检索模式：
    1. semantic_search - 纯语义检索
    2. keyword_search - 纯关键词检索
    3. hybrid_search - 混合检索（语义+关键词）

    混合检索可配合权重设置或Rerank重排使用以获得最佳效果。
    """
    ds_id = get_dataset_id(dataset_id)

    # Build retrieval model
    retrieval_model = {
        "search_method": search_method,
        "top_k": top_k,
        "score_threshold_enabled": score_threshold_enabled,
        "reranking_enable": reranking_enable,
    }

    if score_threshold_enabled:
        retrieval_model["score_threshold"] = score_threshold

    # Handle reranking model
    if reranking_enable:
        retrieval_model["reranking_model"] = {
            "reranking_provider_name": reranking_provider_name,
            "reranking_model_name": reranking_model_name,
        }
    elif search_method == "hybrid_search" and not reranking_enable:
        # Hybrid search with weight settings
        retrieval_model["weights"] = {
            "weight_type": "customized",
            "vector_setting": {
                "vector_weight": vector_weight,
                "embedding_provider_name": "langgenius/siliconflow/siliconflow",
                "embedding_model_name": "BAAI/bge-large-zh-v1.5",
            },
            "keyword_setting": {
                "keyword_weight": round(1 - vector_weight, 2),
            }
        }

    payload = {
        "query": query,
        "retrieval_model": retrieval_model,
    }

    logger.info(f"Retrieving from dataset {ds_id} with method {search_method}")
    result = await dify_request("POST", f"/v1/datasets/{ds_id}/retrieve", json=payload)

    if "error" in result:
        return ToolResult(
            content=[TextContent(type="text", text=f"检索失败: {result.get('detail', result.get('error'))}")],
            structured_content=result,
        )

    # Format results
    records = result.get("records", [])
    if not records:
        return ToolResult(
            content=[TextContent(type="text", text="未找到相关片段")],
            structured_content={"records": []},
        )

    output_lines = [f"检索到 {len(records)} 条相关片段:\n"]
    for i, record in enumerate(records, 1):
        score = record.get("score", 0)
        content = record.get("content", "")
        # Truncate long content
        if len(content) > 500:
            content = content[:500] + "..."
        output_lines.append(f"\n--- 片段 {i} (相似度: {score:.4f}) ---")
        output_lines.append(content)

    return ToolResult(
        content=[TextContent(type="text", text="\n".join(output_lines))],
        structured_content={"records": records, "query": query, "dataset_id": ds_id},
    )


@mcp.tool(description="获取DIFY知识库中的文档列表")
async def list_documents(
    dataset_id: Annotated[str, Field(description="知识库ID或名称")],
    page: Annotated[int, Field(description="页码，默认1")] = 1,
    limit: Annotated[int, Field(description="每页数量，默认20")] = 20,
) -> ToolResult:
    """获取指定知识库中的文档列表。"""
    ds_id = get_dataset_id(dataset_id)

    params = {"page": page, "limit": limit}
    logger.info(f"Listing documents from dataset {ds_id}")

    result = await dify_request("GET", f"/v1/datasets/{ds_id}/documents", params=params)

    if "error" in result:
        return ToolResult(
            content=[TextContent(type="text", text=f"获取文档列表失败: {result.get('detail', result.get('error'))}")],
            structured_content=result,
        )

    data = result.get("data", [])
    total = result.get("total", len(data))

    if not data:
        return ToolResult(
            content=[TextContent(type="text", text=f"知识库中暂无文档（总页数: {total}）")],
            structured_content=result,
        )

    output_lines = [f"文档列表 (共 {total} 个文档):\n"]
    for doc in data:
        name = doc.get("name", "未知")
        doc_id = doc.get("id", "")
        status = doc.get("status", "未知")
        output_lines.append(f"\n- {name} (ID: {doc_id}, 状态: {status})")

    return ToolResult(
        content=[TextContent(type="text", text="\n".join(output_lines))],
        structured_content=result,
    )


@mcp.tool(description="快速将纯文本内容入库到DIFY知识库")
async def create_document_by_text(
    dataset_id: Annotated[str, Field(description="知识库ID或名称")],
    name: Annotated[str, Field(description="文档标题")],
    text: Annotated[str, Field(description="需要入库的完整文本内容")],
    indexing_technique: Annotated[str, Field(description="索引技术: high_quality(高质量) 或 economy(经济型)")] = "high_quality",
) -> ToolResult:
    """
    将纯文本内容快速入库到DIFY知识库。

    适用于：
    - 快速备忘录入库
    - 聊天记录归档到知识库
    - 临时文档入库
    """
    ds_id = get_dataset_id(dataset_id)

    payload = {
        "name": name,
        "text": text,
        "indexing_technique": indexing_technique,
        "process_rule": {
            "mode": "automatic"
        }
    }

    logger.info(f"Creating document in dataset {ds_id}")
    result = await dify_request("POST", f"/v1/datasets/{ds_id}/document/create-by-text", json=payload)

    if "error" in result:
        return ToolResult(
            content=[TextContent(type="text", text=f"文档入库失败: {result.get('detail', result.get('error'))}")],
            structured_content=result,
        )

    doc_id = result.get("document", {}).get("id", "未知")
    return ToolResult(
        content=[TextContent(type="text", text=f"文档创建成功！\n文档ID: {doc_id}\n标题: {name}")],
        structured_content=result,
    )


@mcp.resource(uri="dify:///datasets", name="All Datasets",
              description="列出DIFY知识库映射表",
              mime_type="text/plain")
def get_all_datasets() -> str:
    """返回预定义的知识库映射表。"""
    lines = ["DIFY 知识库映射表:\n"]
    for ds_id, info in DATASETS.items():
        lines.append(f"- {info['name']}: {ds_id}")
        lines.append(f"  描述: {info['description']}")
        lines.append(f"  适用场景: {', '.join(info['use_cases'])}")
    return "\n".join(lines)


@mcp.resource(uri="dify:///{dataset_id}/info", name="Dataset Info",
              description="获取知识库信息",
              mime_type="text/plain")
def get_dataset_info(dataset_id: str) -> str:
    """返回指定知识库的详细信息。"""
    ds_id = get_dataset_id(dataset_id)
    info = get_dataset_info_by_id(ds_id)
    return f"知识库名称: {info['name']}\nDataset ID: {ds_id}\n描述: {info['description']}\n适用场景: {', '.join(info['use_cases'])}"


# ============== PROMPTS ==============

@mcp.prompt(title="选择知识库", description="根据用户问题选择最合适的知识库")
def choose_dataset(question: str) -> str:
    """
    根据用户问题，参考以下知识库列表，决定应该查询哪个知识库。

    知识库列表：
    1. 车型知识库 (9e07fcf2-56cf-4f2c-b115-8727e721fbd3)
       - 包含车型相关文档，如车型参数、配置、特性等
       - 适用场景：询问车型配置、车型参数对比、车型功能介绍

    2. 国际-大区知识库 (486476a8-15f6-4359-bcb5-6efd40d90373)
       - 国际大区相关数据，如亚太区、欧洲区等
       - 适用场景：大区信息查询、跨大区业务问题

    3. 国际-国家知识库 (90560d64-db69-4c66-88ca-9c86a340dd5d)
       - 国家级数据，包含各个国家的特定信息
       - 适用场景：国家政策查询、国家市场数据、国家法规要求

    4. 国际问答对-V3 (ffa84ba6-4ec9-44a0-8f6d-594b27f7a829)
       - 当前默认测试的高质量问答库，包含各类常见问题及答案
       - 适用场景：通用问答、常见问题解答、业务咨询

    5. 同环比-国际问答对-V2 (959f346f-f950-480c-a1d7-d792ad10be33)
       - 历史版本数据，主要用于同比环比相关问题
       - 适用场景：同期对比、环比分析、历史数据查询

    用户问题：{question}

    请分析问题意图，选择最匹配的知识库。如果不确定，优先选择"国际问答对-V3"。
    """


@mcp.prompt(title="配置检索参数", description="根据检索需求生成合适的检索参数")
def configure_retrieval(
    search_type: str,
    need_rerank: bool = False,
    precision_focus: bool = False
) -> str:
    """
    根据需求生成检索参数建议。

    检索类型选项：
    - semantic_search: 纯语义检索，适合语义理解类问题
    - keyword_search: 纯关键词检索，适合精确术语匹配
    - hybrid_search: 混合检索，结合两者优点

    Rerank重排：
    - 开启Rerank可以获得更精确的排序结果，但响应稍慢
    - 建议：对精度要求高时开启

    返回推荐的参数组合。
    """
    recommendations = []

    if search_type == "semantic_search":
        recommendations.append("- 使用 semantic_search（语义检索）")
        recommendations.append("- 默认 top_k=3，如需更多结果可调整")
    elif search_type == "keyword_search":
        recommendations.append("- 使用 keyword_search（关键词检索）")
        recommendations.append("- 适合精确匹配场景")
    elif search_type == "hybrid_search":
        recommendations.append("- 使用 hybrid_search（混合检索）")
        if need_rerank:
            recommendations.append("- 强烈建议开启 reranking_enable=true")
            recommendations.append("- 配合 reranking_model 效果最佳")
        else:
            recommendations.append("- 建议设置 vector_weight=0.7（语义:关键词=7:3）")

    if precision_focus:
        recommendations.append("- 开启 score_threshold_enabled=true")
        recommendations.append("- 设置合适的 score_threshold（建议0.5）")

    return "\n".join(recommendations) if recommendations else "使用默认参数即可"


@mcp.prompt(title="综合问答流程", description="用于处理用户知识库问答的完整流程指导")
def knowledge_qa_flow(question: str) -> str:
    """
    处理用户知识库问答的推荐流程：

    1. 分析问题 -> 确定知识库
       - 问车型/配置 → 车型知识库
       - 问大区/区域 → 国际-大区知识库
       - 问国家/国际市场 → 国际-国家知识库
       - 问通用问题/业务咨询 → 国际问答对-V3
       - 问同比/环比/历史 → 同环比-国际问答对-V2

    2. 选择检索策略
       - 口语化问题 → semantic_search
       - 精确术语/编号 → keyword_search
       - 混合场景 → hybrid_search + rerank

    3. 调用 retrieve_segments 工具

    4. 如结果不满意，可调整参数重试：
       - 增加 top_k 获取更多结果
       - 开启 reranking_enable 提高精度
       - 调整 vector_weight 改变语义/关键词比例

    用户问题：{question}
    """



async def main():
    parser = argparse.ArgumentParser(description='DIFY Knowledge Base MCP Server')
    parser.add_argument('--mode', choices=['stdio', 'sse', 'http', 'streamable-http'],
                        default=os.getenv('MCP_TRANSPORT_MODE', 'stdio'),
                        help='Transport mode (default: stdio)')
    parser.add_argument('--host', default='localhost',
                        help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=9879,
                        help='Server port (default: 9879)')
    parser.add_argument('--test', action='store_true',
                        help='Run in test mode')

    args = parser.parse_args()
    logger.info(f"Starting DIFY MCP Server with mode={args.mode}, host={args.host}, port={args.port}")

    if args.test:
        # Test connectivity
        result = await dify_request("GET", "/v1/datasets")
        if "error" in result:
            logger.error(f"Connection test failed: {result}")
        else:
            logger.info("Connection test successful!")
            logger.info(f"Response: {result}")
        return

    await mcp.run_async(transport=args.mode, host=args.host, port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
