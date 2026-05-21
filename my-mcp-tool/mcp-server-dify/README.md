# DIFY Knowledge Base MCP Server

The DIFY Knowledge Base MCP Server acts as a bridge between AI assistants and DIFY knowledge base. It enables semantic search, keyword search, hybrid search with reranking, document listing, and text-based document creation.

## Features

- **Semantic Search**: Pure semantic similarity-based retrieval
- **Keyword Search**: Full-text keyword matching
- **Hybrid Search**: Combined semantic + keyword with customizable weights
- **Rerank Support**: Neural model reranking for improved result quality
- **Score Threshold**: Filter results by relevance score
- **Document Management**: List documents and create documents from text

## Configuration

### Environment Variables

- `DIFY_API_BASE_URL`: API base URL (default: http://10.30.11.215:9879)
- `DIFY_API_KEY`: API authentication key
- `MCP_TRANSPORT_MODE`: Transport mode (stdio/streamable-http)

### Quick Start

```bash
# Test connection
uv run mcp-server-dify --test

# Run server
uv run mcp-server-dify --mode stdio
```

### Claude Code Configuration

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
      ]
    }
  }
}
```

## Tools

### retrieve_segments

Core knowledge base retrieval tool supporting multiple search strategies.

**Parameters:**
- `query`: Search query text
- `dataset_id`: Dataset ID or name (supports: 车型知识库, 国际-大区知识库, 国际-国家知识库, 国际问答对-V3, 同环比-国际问答对-V2)
- `search_method`: semantic_search | keyword_search | hybrid_search
- `top_k`: Number of results (1-20)
- `score_threshold_enabled`: Enable score filtering
- `score_threshold`: Score threshold (0-1)
- `reranking_enable`: Enable rerank model
- `vector_weight`: Semantic weight for hybrid search (0-1)

### list_documents

List documents in a dataset.

**Parameters:**
- `dataset_id`: Dataset ID or name
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)

### create_document_by_text

Quick text ingestion to knowledge base.

**Parameters:**
- `dataset_id`: Dataset ID or name
- `name`: Document title
- `text`: Full text content
- `indexing_technique`: high_quality | economy

## Resources

- `dify:///datasets`: Lists all predefined dataset mappings with descriptions
- `dify:///{dataset_id}/info`: Get dataset information

## Knowledge Base Selection

The MCP provides prompts to help LLM choose the right dataset:

| 知识库 | 适用场景 |
|---|---|
| 车型知识库 | 车型配置、参数对比、功能介绍 |
| 国际-大区知识库 | 大区信息、跨大区业务 |
| 国际-国家知识库 | 国家政策、市场数据、法规要求 |
| 国际问答对-V3 | 通用问答、常见问题、业务咨询 |
| 同环比-国际问答对-V2 | 同期对比、环比分析、历史数据 |

## Prompts

- `choose_dataset(question)`: 根据用户问题选择最合适的知识库
- `configure_retrieval(search_type, need_rerank, precision_focus)`: 生成检索参数建议
- `knowledge_qa_flow(question)`: 综合问答流程指导
