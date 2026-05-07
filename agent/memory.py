"""SQLite-backed chat history."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(SCHEMA)


def new_session(title: str = "New chat") -> int:
    init_db()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO sessions(title, created_at) VALUES (?, ?)",
            (title, time.time()),
        )
        return cur.lastrowid


def list_sessions() -> list[dict]:
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()
    return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]


def rename_session(session_id: int, title: str) -> None:
    with _conn() as c:
        c.execute("UPDATE sessions SET title=? WHERE id=?", (title, session_id))


def delete_session(session_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE id=?", (session_id,))


def add_message(session_id: int, role: str, content: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, time.time()),
        )


def get_messages(session_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]
