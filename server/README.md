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
- `GET /api/config/dify`
- `GET /api/config/query`
- `POST /api/knowledge/retrieve`
- `POST /api/query/validate`
- `POST /api/query/execute`
- `GET /api/downloads/mock-detail.csv`

## Configuration

Local environment variables are loaded from the project root `.env` first, then
from `server/.env` if it exists. Use `.env.example` as the safe template.

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

## Dify Knowledge Retrieval

The backend exposes a stable retrieval boundary before replacing mock knowledge
lookups with real Dify.

- Status/config endpoint: `GET /api/config/dify`
- Retrieval endpoint: `POST /api/knowledge/retrieve`
- Default provider: `mock-dify`
- Enable real Dify: `CHATBI_DIFY_ENABLED=true`
- Required for real Dify: `DIFY_API_KEY`
- Optional base URL override: `DIFY_API_BASE_URL=http://10.30.11.215:9879`

When real Dify is disabled, missing, or unreachable, the endpoint returns mock
records with a `fallback` reason while preserving the same response shape.

## MySQL Query Service

The query service is guarded by `app/sql_guard.py` before any real database call.
Only single-statement `SELECT` queries against configured data asset tables are
allowed.

- Query provider: `CHATBI_QUERY_PROVIDER=mock | mysql`
- Config endpoint: `GET /api/config/query`
- SQL validation: `POST /api/query/validate`
- SQL execution: `POST /api/query/execute`

For direct MySQL access, fill:

```env
CHATBI_QUERY_PROVIDER=mysql
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_USER=your-user
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=your-database
```

For MySQL behind an SSH host, fill the remote MySQL address in `MYSQL_HOST` and
enable the tunnel:

```env
MYSQL_SSH_ENABLED=true
MYSQL_SSH_HOST=your-ssh-host
MYSQL_SSH_PORT=22
MYSQL_SSH_USER=your-ssh-user
MYSQL_SSH_PASSWORD=
MYSQL_SSH_PRIVATE_KEY_PATH=C:\path\to\private_key
MYSQL_SSH_PRIVATE_KEY_PASSPHRASE=
```

The service opens the SSH tunnel only for the query call and never returns
passwords or private key values from config endpoints.
