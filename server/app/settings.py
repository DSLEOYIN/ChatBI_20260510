import os
from dataclasses import dataclass
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent


def load_env_files() -> None:
    for path in (PROJECT_ROOT / ".env", SERVER_DIR / ".env"):
        if path.exists():
            load_env_file(path)


def load_env_file(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
        return
    except ImportError:
        pass

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default
    path = Path(raw)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    chatbi_db_path: Path
    chatbi_data_assets_path: Path
    chatbi_dify_enabled: bool
    dify_api_base_url: str
    dify_api_key: str
    dify_reranking_provider: str
    dify_reranking_model: str
    dify_embedding_provider: str
    dify_embedding_model: str
    chatbi_query_provider: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    mysql_connect_timeout: int
    mysql_ssh_enabled: bool
    mysql_ssh_host: str
    mysql_ssh_port: int
    mysql_ssh_user: str
    mysql_ssh_password: str
    mysql_ssh_private_key_path: Path | None
    mysql_ssh_private_key_passphrase: str
    mysql_ssh_local_port: int
    tavily_api_key: str


def load_settings() -> Settings:
    load_env_files()
    return Settings(
        chatbi_db_path=env_path("CHATBI_DB_PATH", PROJECT_ROOT / "chatbi_mock.db"),
        chatbi_data_assets_path=env_path("CHATBI_DATA_ASSETS_PATH", SERVER_DIR / "config" / "data_assets.json"),
        chatbi_dify_enabled=env_bool("CHATBI_DIFY_ENABLED", False),
        dify_api_base_url=os.getenv("DIFY_API_BASE_URL", "http://10.30.11.215:9879").rstrip("/"),
        dify_api_key=os.getenv("DIFY_API_KEY", ""),
        dify_reranking_provider=os.getenv("DIFY_RERANKING_PROVIDER", "langgenius/siliconflow/siliconflow"),
        dify_reranking_model=os.getenv("DIFY_RERANKING_MODEL", "netease-youdao/bce-reranker-base_v1"),
        dify_embedding_provider=os.getenv("DIFY_EMBEDDING_PROVIDER", "langgenius/siliconflow/siliconflow"),
        dify_embedding_model=os.getenv("DIFY_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"),
        chatbi_query_provider=os.getenv("CHATBI_QUERY_PROVIDER", "mock").lower(),
        mysql_host=os.getenv("MYSQL_HOST", ""),
        mysql_port=env_int("MYSQL_PORT", 3306),
        mysql_user=os.getenv("MYSQL_USER", ""),
        mysql_password=os.getenv("MYSQL_PASSWORD", ""),
        mysql_database=os.getenv("MYSQL_DATABASE", ""),
        mysql_connect_timeout=env_int("MYSQL_CONNECT_TIMEOUT", 15),
        mysql_ssh_enabled=env_bool("MYSQL_SSH_ENABLED", False),
        mysql_ssh_host=os.getenv("MYSQL_SSH_HOST", ""),
        mysql_ssh_port=env_int("MYSQL_SSH_PORT", 22),
        mysql_ssh_user=os.getenv("MYSQL_SSH_USER", ""),
        mysql_ssh_password=os.getenv("MYSQL_SSH_PASSWORD", ""),
        mysql_ssh_private_key_path=env_path("MYSQL_SSH_PRIVATE_KEY_PATH", Path("")) if os.getenv("MYSQL_SSH_PRIVATE_KEY_PATH") else None,
        mysql_ssh_private_key_passphrase=os.getenv("MYSQL_SSH_PRIVATE_KEY_PASSPHRASE", ""),
        mysql_ssh_local_port=env_int("MYSQL_SSH_LOCAL_PORT", 0),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
    )


settings = load_settings()
