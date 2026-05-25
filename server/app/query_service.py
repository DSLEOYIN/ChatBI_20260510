import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.models.schemas import QueryRequest, QueryResult
from app.settings import settings
from app.sql_guard import validate_sql


MOCK_ROWS = [
    {"model_name": "GS8", "terminal_qty": 920, "target_qty": 1180, "achievement_rate": "78.0%"},
    {"model_name": "EMZOOM", "terminal_qty": 1560, "target_qty": 1420, "achievement_rate": "109.9%"},
]


def query_config_metadata() -> dict[str, Any]:
    return {
        "provider": settings.chatbi_query_provider,
        "mysql": {
            "host_configured": bool(settings.mysql_host),
            "port": settings.mysql_port,
            "user_configured": bool(settings.mysql_user),
            "password_configured": bool(settings.mysql_password),
            "database_configured": bool(settings.mysql_database),
            "connect_timeout": settings.mysql_connect_timeout,
        },
        "ssh": {
            "enabled": settings.mysql_ssh_enabled,
            "host_configured": bool(settings.mysql_ssh_host),
            "port": settings.mysql_ssh_port,
            "user_configured": bool(settings.mysql_ssh_user),
            "password_configured": bool(settings.mysql_ssh_password),
            "private_key_configured": bool(settings.mysql_ssh_private_key_path),
            "local_port": settings.mysql_ssh_local_port,
        },
    }


def validate_query(sql: str):
    return validate_sql(sql)


def execute_query(request: QueryRequest) -> QueryResult:
    start = time.perf_counter()
    validation = validate_sql(request.sql)
    if not validation.valid:
        return QueryResult(
            provider=active_provider(),
            sql=request.sql,
            validation=validation,
            columns=[],
            rows=[],
            row_count=0,
            elapsed_ms=elapsed_ms(start),
            connection=connection_summary(),
        )

    provider = active_provider()
    try:
        if settings.chatbi_query_provider == "mysql":
            rows = execute_mysql_query(validation.sql, request.limit)
        else:
            rows = MOCK_ROWS[: request.limit]
    except Exception as exc:
        return QueryResult(
            provider=provider,
            sql=validation.sql,
            validation=validation,
            columns=[],
            rows=[],
            row_count=0,
            elapsed_ms=elapsed_ms(start),
            connection=connection_summary(),
            error={"type": type(exc).__name__, "message": str(exc)},
        )

    columns = list(rows[0].keys()) if rows else []
    return QueryResult(
        provider=provider,
        sql=validation.sql,
        validation=validation,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        elapsed_ms=elapsed_ms(start),
        connection=connection_summary(),
    )


def active_provider() -> str:
    return "mysql" if settings.chatbi_query_provider == "mysql" else "mock"


def elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def connection_summary() -> dict[str, Any]:
    return {
        "provider": active_provider(),
        "ssh_tunnel": settings.mysql_ssh_enabled,
        "mysql_host": settings.mysql_host if settings.chatbi_query_provider == "mysql" else "mock",
        "mysql_port": settings.mysql_port if settings.chatbi_query_provider == "mysql" else None,
        "database_configured": bool(settings.mysql_database),
    }


def execute_mysql_query(sql: str, limit: int) -> list[dict[str, Any]]:
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("pymysql is required for CHATBI_QUERY_PROVIDER=mysql") from exc

    with mysql_endpoint() as endpoint:
        host, port = endpoint
        connection = pymysql.connect(
            host=host,
            port=port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            connect_timeout=settings.mysql_connect_timeout,
            read_timeout=settings.mysql_connect_timeout,
            write_timeout=settings.mysql_connect_timeout,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(apply_limit(sql, limit))
                return list(cursor.fetchall())
        finally:
            connection.close()


@contextmanager
def mysql_endpoint() -> Iterator[tuple[str, int]]:
    if not settings.mysql_ssh_enabled:
        yield settings.mysql_host, settings.mysql_port
        return

    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError as exc:
        raise RuntimeError("sshtunnel is required when MYSQL_SSH_ENABLED=true") from exc

    ssh_kwargs: dict[str, Any] = {
        "ssh_address_or_host": (settings.mysql_ssh_host, settings.mysql_ssh_port),
        "ssh_username": settings.mysql_ssh_user,
        "remote_bind_address": (settings.mysql_host, settings.mysql_port),
        "local_bind_address": ("127.0.0.1", settings.mysql_ssh_local_port),
    }
    if settings.mysql_ssh_private_key_path:
        ssh_kwargs["ssh_pkey"] = str(settings.mysql_ssh_private_key_path)
        if settings.mysql_ssh_private_key_passphrase:
            ssh_kwargs["ssh_private_key_password"] = settings.mysql_ssh_private_key_passphrase
    elif settings.mysql_ssh_password:
        ssh_kwargs["ssh_password"] = settings.mysql_ssh_password

    with SSHTunnelForwarder(**ssh_kwargs) as tunnel:
        yield "127.0.0.1", tunnel.local_bind_port


def apply_limit(sql: str, limit: int) -> str:
    stripped = sql.strip().rstrip(";")
    if " limit " in stripped.lower():
        return stripped
    return f"{stripped} LIMIT {limit}"
