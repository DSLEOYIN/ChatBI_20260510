import json
import sqlite3
from pathlib import Path
from threading import Lock

from app.mock.engine import now_iso

DB_PATH = Path(__file__).resolve().parents[2] / "chatbi_mock.db"
_LOCK = Lock()


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                pinned INTEGER DEFAULT 0
            )
            """
        )
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN pinned INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
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


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
