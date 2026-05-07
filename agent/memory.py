"""SQLite-backed chat history."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH


VALID_MODES = ("ultron", "chat", "coder")
DEFAULT_MODE = "ultron"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    mode TEXT NOT NULL DEFAULT 'ultron'
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


def _migrate_add_mode(c: sqlite3.Connection) -> None:
    cols = [r[1] for r in c.execute("PRAGMA table_info(sessions)").fetchall()]
    if "mode" not in cols:
        c.execute("ALTER TABLE sessions ADD COLUMN mode TEXT NOT NULL DEFAULT 'ultron'")


def init_db() -> None:
    with _conn() as c:
        c.executescript(SCHEMA)
        _migrate_add_mode(c)
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_mode ON sessions(mode)")


def _norm_mode(mode: str | None) -> str:
    return mode if mode in VALID_MODES else DEFAULT_MODE


def new_session(title: str = "New chat", mode: str = DEFAULT_MODE) -> int:
    init_db()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO sessions(title, created_at, mode) VALUES (?, ?, ?)",
            (title, time.time(), _norm_mode(mode)),
        )
        return cur.lastrowid


def list_sessions(mode: str | None = None) -> list[dict]:
    init_db()
    with _conn() as c:
        if mode is None:
            rows = c.execute(
                "SELECT id, title, created_at, mode FROM sessions ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id, title, created_at, mode FROM sessions WHERE mode = ? ORDER BY created_at DESC",
                (_norm_mode(mode),),
            ).fetchall()
    return [{"id": r[0], "title": r[1], "created_at": r[2], "mode": r[3]} for r in rows]


def get_session_mode(session_id: int) -> str | None:
    with _conn() as c:
        row = c.execute("SELECT mode FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return row[0] if row else None


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
