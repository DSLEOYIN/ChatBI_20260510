# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DIFY Knowledge Base MCP Server - A bridge between AI assistants and DIFY knowledge base, built using FastMCP framework. Enables semantic search, keyword search, hybrid search, document management, and text-based document creation through the Model Context Protocol (MCP).

## Development Commands

**Local Development:**
```bash
# Run the server directly for testing
uv run mcp-server-dify

# Run with test mode to verify connectivity
uv run mcp-server-dify --test

# Run in Streamable HTTP mode (recommended for integration)
export MCP_TRANSPORT_MODE=streamable-http
uv run mcp-server-dify --port 9879
```

## Architecture Overview

### Core Components

- **`src/mcp_server_dify/server.py`**: Main server implementation containing all MCP tools, resources, and API client logic
- **`src/mcp_server_dify/__init__.py`**: Entry point that starts the async server

### Tool Categories

1. **Retrieval Tools**:
   - `retrieve_segments`: Core knowledge base search supporting semantic, keyword, and hybrid search modes
   - Supports Rerank model re-ranking for improved results
   - Supports score threshold filtering

2. **Document Management Tools**:
   - `list_documents`: Get document list from a dataset
   - `create_document_by_text`: Quick text ingestion to knowledge base

### Resource Endpoints

- `dify:///datasets`: Lists all predefined dataset mappings
- `dify:///{dataset_id}/info`: Get dataset information

### Predefined Dataset Mappings

| 知识库名称 | Dataset ID | 适用场景 |
|---|---|---|
| 车型知识库 | 9e07fcf2-56cf-4f2c-b115-8727e721fbd3 | 车型配置、参数对比、功能介绍 |
| 国际-大区知识库 | 486476a8-15f6-4359-bcb5-6efd40d90373 | 大区信息、跨大区业务 |
| 国际-国家知识库 | 90560d64-db69-4c66-88ca-9c86a340dd5d | 国家政策、市场数据、法规要求 |
| 国际问答对-V3 | ffa84ba6-4ec9-44a0-8f6d-594b27f7a829 | 通用问答、常见问题、业务咨询 |
| 同环比-国际问答对-V2 | 959f346f-f950-480c-a1d7-d792ad10be33 | 同期对比、环比分析、历史数据 |

### Prompts (for LLM guidance)

- `choose_dataset(question)`: 根据用户问题选择最合适的知识库
- `configure_retrieval(search_type, need_rerank, precision_focus)`: 生成检索参数建议
- `knowledge_qa_flow(question)`: 综合问答流程指导

## Configuration

Environment variables for API connection:
- `DIFY_API_BASE_URL`: DIFY API base URL (default: http://10.30.11.215:9879)
- `DIFY_API_KEY`: DIFY API key (default: dataset-S5L6smkj8ovnSz8rMl5DZUvj)
- `MCP_TRANSPORT_MODE`: Communication mode (stdio/streamable-http/sse)

## Code Patterns

### Error Handling
- All API errors return structured error messages
- Tools return `ToolResult` with both text content and structured content
- Async/await pattern used for HTTP requests via httpx

### Tool Result Format
All tools return `ToolResult` with:
- `content`: TextContent array for human-readable output
- `structured_content`: JSON data for programmatic consumption

## MCP Client Configuration

```json
{
  "mcpServers": {
    "mcp-server-dify": {
      "command": "uv",
      "args": [
        "--directory",
        "path/to/mcp-server-dify",
        "run",
        "mcp-server-dify"
      ],
      "env": {
        "DIFY_API_BASE_URL": "http://10.30.11.215:9879",
        "DIFY_API_KEY": "dataset-S5L6smkj8ovnSz8rMl5DZUvj"
      }
    }
  }
}
```

Or using Streamable HTTP mode:
```json
{
  "mcpServers": {
    "mcp-server-dify": {
      "url": "http://localhost:9879/mcp"
    }
  }
}
```
