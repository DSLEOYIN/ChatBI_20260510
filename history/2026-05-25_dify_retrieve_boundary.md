# 2026-05-25 Dify Retrieve API 边界封装

本轮继续推进 P2「真实 API 替换准备」第三项：先封装 Dify 知识库 Retrieve API，再为后续 MCP/Agent 替换预留稳定契约。当前实现默认不依赖真实 Dify 服务，只有显式打开环境变量时才会请求真实接口，避免本地 mock 演示被内网服务或密钥状态阻断。

## 完成内容

1. 新增 `server/app/dify.py`，集中封装 Dify dataset 映射、检索 payload 构造、真实请求、mock fallback 和返回结构归一化。
2. 新增 `KnowledgeRetrieveRequest` / `KnowledgeRetrieveResult` schema，约束检索参数与返回结构。
3. 新增 `GET /api/config/dify`，用于查看当前 provider、base URL、密钥配置状态、dataset 映射和默认检索参数。
4. 新增 `POST /api/knowledge/retrieve`，支持 `semantic_search`、`keyword_search`、`hybrid_search`、阈值过滤、Rerank 开关和混合检索权重。
5. 默认 provider 为 `mock-dify`；当 `CHATBI_DIFY_ENABLED=true` 且配置 `DIFY_API_KEY` 时，请求真实 Dify `/v1/datasets/{dataset_id}/retrieve`。
6. 真实 Dify 不可达时自动返回 mock records，并在 `fallback.reason` 中说明降级原因。
7. 前端 `client/src/services/api.js` 新增 `getDifyConfig` 与 `retrieveKnowledge`，为后续 UI 或 Agent 面板消费该契约预留入口。
8. `MOCK_API_CONTRACT` 补充 `knowledge_retrieve` 与 `dify_status` 能力说明。
9. `server/README.md` 补充 Dify 配置和接口说明。

## 涉及文件

- `server/app/dify.py`
- `server/app/models/schemas.py`
- `server/app/api/routes.py`
- `server/app/mock/catalog.py`
- `server/requirements.txt`
- `server/README.md`
- `client/src/services/api.js`

## 配置方式

```bash
CHATBI_DIFY_ENABLED=true
DIFY_API_KEY=your-dify-dataset-api-key
DIFY_API_BASE_URL=http://10.30.11.215:9879
```

## 当前 P2 状态

- [x] 会话接口：SQLite mock 存储升级为可迁移存储结构。
- [x] 数据资产 / 字段口径：从 mock 配置升级为 JSON 外部配置。
- [x] Dify 知识库检索：先封装 Retrieve API，保留 mock fallback，后续可继续封装为 MCP/Agent 工具。
- [ ] MySQL 查询：只读 SELECT，增加 SQL 安全校验与 allowed tables 过滤。
- [ ] Tavily MCP 搜索：替换固定 mock 搜索结果。
- [ ] LangGraph Agent：替换当前硬编码 intent/mock engine。
- [ ] 权限系统：MVP 后补充用户角色、可访问场景、可访问表、可下载字段。
