# ChatBI Mock Backend

第一阶段后端 mock 服务，用于跑通 PRD 中的会话、流式问答、动态画布、配置和下载接口。

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Main APIs

- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `GET /api/config/skills`
- `GET /api/config/data-assets`
- `GET /api/downloads/mock-detail.csv`
