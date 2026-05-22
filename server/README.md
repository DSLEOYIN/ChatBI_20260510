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
- `GET /api/config/storage`
- `GET /api/downloads/mock-detail.csv`

## Configuration

Data assets and metric definitions are loaded from JSON config by default:

- Default catalog: `config/data_assets.json`
- Optional override: `CHATBI_DATA_ASSETS_PATH=/absolute/path/data_assets.json`
- Fallback: built-in mock constants in `app/mock/catalog.py`

`GET /api/config/data-assets` includes the active source, path, assets, and
metric definitions so local runs can verify which catalog is being used.

## Storage

The mock backend still uses SQLite by default, but the schema is now managed by
versioned migrations in `app/storage.py`.

- Default database: `../chatbi_mock.db`
- Optional override: `CHATBI_DB_PATH=/absolute/path/chatbi_mock.db`
- Migration metadata table: `schema_migrations`
- Current schema version: `2`

`GET /api/config/storage` returns the active database path, schema version, and
applied migrations for local verification.
