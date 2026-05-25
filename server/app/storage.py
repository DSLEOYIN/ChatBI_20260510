import json
import sqlite3
from pathlib import Path
from threading import Lock

from app.mock.engine import now_iso
from app.settings import settings

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "chatbi_mock.db"
DB_PATH = settings.chatbi_db_path
_LOCK = Lock()


def init_db() -> None:
    migrate_db()


def migrate_db() -> None:
    with _LOCK, connect() as conn:
        ensure_migration_table(conn)
        for version, description, migration in MIGRATIONS:
            if has_migration(conn, version):
                continue
            migration(conn)
            conn.execute(
                "INSERT INTO schema_migrations(version, description, applied_at) VALUES (?, ?, ?)",
                (version, description, now_iso()),
            )


def ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def has_migration(conn: sqlite3.Connection, version: int) -> bool:
    row = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,)).fetchone()
    return row is not None


def migration_001_base_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    )


def migration_002_pinned_and_indexes(conn: sqlite3.Connection) -> None:
    if not column_exists(conn, "conversations", "pinned"):
        conn.execute("ALTER TABLE conversations ADD COLUMN pinned INTEGER DEFAULT 0")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, pinned DESC, updated_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id, id)")


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


MIGRATIONS = [
    (1, "create conversation and message tables", migration_001_base_schema),
    (2, "add conversation pinning and lookup indexes", migration_002_pinned_and_indexes),
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def storage_metadata() -> dict:
    with connect() as conn:
        ensure_migration_table(conn)
        rows = conn.execute(
            "SELECT version, description, applied_at FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
    latest = rows[-1]["version"] if rows else 0
    return {
        "engine": "sqlite",
        "database": str(DB_PATH),
        "schema_version": latest,
        "available_migrations": len(MIGRATIONS),
        "migrations": [dict(row) for row in rows],
    }


def create_conversation_record(conversation: dict) -> None:
    with _LOCK, connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO conversations(id, user_id, title, created_at, updated_at, pinned) VALUES (?, ?, ?, ?, ?, ?)",
            (
                conversation["id"],
                conversation["user_id"],
                conversation["title"],
                conversation["created_at"],
                conversation["updated_at"],
                conversation.get("pinned", 0),
            ),
        )


def list_conversation_records(user_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, title, created_at, updated_at, pinned FROM conversations WHERE user_id = ? ORDER BY pinned DESC, updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation_record(conversation_id: str) -> dict | None:
    with connect() as conn:
        conversation = conn.execute(
            "SELECT id, user_id, title, created_at, updated_at, pinned FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if not conversation:
            return None
        messages = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
    data = dict(conversation)
    data["messages"] = [
        {
            "role": row["role"],
            "content": json.loads(row["content"]) if row["role"] == "assistant" else row["content"],
            "created_at": row["created_at"],
        }
        for row in messages
    ]
    return data


def delete_conversation_record(conversation_id: str) -> None:
    with _LOCK, connect() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def pin_conversation_record(conversation_id: str, pinned: bool) -> None:
    with _LOCK, connect() as conn:
        conn.execute("UPDATE conversations SET pinned = ? WHERE id = ?", (1 if pinned else 0, conversation_id))


def append_exchange(conversation_id: str, user_content: str, result: dict) -> None:
    ts = now_iso()
    title = user_content[:18] + ("..." if len(user_content) > 18 else "")
    with _LOCK, connect() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, ts, conversation_id),
        )
        conn.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, "user", user_content, ts),
        )
        conn.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, "assistant", json.dumps(result, ensure_ascii=False), ts),
        )
