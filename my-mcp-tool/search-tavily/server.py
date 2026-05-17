import os
import json
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

# 1. 初始化名为 "tavily-search" 的 MCP Server
mcp = FastMCP("tavily-search")

# 2. 从环境变量读取你的 API Key 并初始化客户端
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("严重错误：未检测到 TAVILY_API_KEY 环境变量！")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# 3. 定义工具并暴露给大模型
@mcp.tool()
def search_web(query: str, search_depth: str = "advanced", include_answer: bool = True) -> str:
    """
    使用 Tavily 搜索引擎进行深度网页搜索。
    :param query: 你想要搜索的关键词或完整问题
    :param search_depth: 搜索深度，默认 "basic"（快速），可选 "advanced"（更深度的聚合，消耗更多额度）
    :param include_answer: 是否让 Tavily 直接返回一段基于搜索结果生成的总结性答案
    :return: JSON 格式的搜索结果
    """
    try:
        # 调用 Tavily 接口
        response = tavily_client.search(
            query=query, 
            search_depth=search_depth,
            include_answer=include_answer
        )
        return json.dumps(response, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"搜索执行失败: {str(e)}"

if __name__ == "__main__":
    # 4. 以 stdio 流模式运行，专门对接容器化调用
    mcp.run()