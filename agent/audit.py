"""Append-only audit log of every tool call. Read via the API for the dashboard."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager

from config import DATA_DIR


AUDIT_DB = DATA_DIR / "audit.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    tool TEXT NOT NULL,
    args TEXT,
    result TEXT,
    duration_ms REAL,
    status TEXT,
    session_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts);
CREATE INDEX IF NOT EXISTS idx_audit_tool ON audit(tool);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(AUDIT_DB)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init():
    with _conn() as c:
        c.executescript(SCHEMA)


_init()


def log(
    tool: str,
    args: dict | str | None = None,
    result: str = "",
    duration_ms: float = 0.0,
    status: str = "ok",
    session_id: int | None = None,
) -> None:
    args_str = json.dumps(args) if isinstance(args, dict) else (str(args) if args else None)
    with _conn() as c:
        c.execute(
            "INSERT INTO audit(ts, tool, args, result, duration_ms, status, session_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (time.time(), tool, args_str, str(result)[:2000], duration_ms, status, session_id),
        )


def recent(limit: int = 100, tool: str | None = None) -> list[dict]:
    q = "SELECT id, ts, tool, args, result, duration_ms, status, session_id FROM audit"
    args = []
    if tool:
        q += " WHERE tool=?"
        args.append(tool)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    return [
        {
            "id": r[0], "ts": r[1], "tool": r[2],
            "args": r[3], "result": r[4],
            "duration_ms": r[5], "status": r[6], "session_id": r[7],
        }
        for r in rows
    ]


def stats(window_hours: int = 24) -> dict:
    cutoff = time.time() - window_hours * 3600
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM audit WHERE ts>=?", (cutoff,)).fetchone()[0]
        by_tool = c.execute(
            "SELECT tool, COUNT(*) c, AVG(duration_ms) avg_ms, "
            "SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) ok_count "
            "FROM audit WHERE ts>=? GROUP BY tool ORDER BY c DESC LIMIT 20",
            (cutoff,),
        ).fetchall()
    return {
        "window_hours": window_hours,
        "total_calls": total,
        "by_tool": [
            {
                "tool": r[0], "count": r[1],
                "avg_ms": round(r[2] or 0, 1),
                "success_rate": round((r[3] / r[1]) * 100, 1) if r[1] else 0,
            }
            for r in by_tool
        ],
    }
