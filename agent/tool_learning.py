"""Track tool success rates per query category. Bias router toward winners over time."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

from config import DATA_DIR


LEARN_DB = DATA_DIR / "tool_learning.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    tool TEXT NOT NULL,
    success INTEGER NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tool_cat ON tool_outcomes(category, tool);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(LEARN_DB)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init():
    with _conn() as c:
        c.executescript(SCHEMA)


_init()


def record_outcome(category: str, tool: str, success: bool) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO tool_outcomes(category, tool, success, ts) VALUES (?,?,?,?)",
            (category, tool, 1 if success else 0, time.time()),
        )


def tool_score(category: str, tool: str) -> float:
    """0..1 success rate over the last 50 calls in this category. Returns 0.5 with no data."""
    with _conn() as c:
        rows = c.execute(
            "SELECT success FROM tool_outcomes WHERE category=? AND tool=? "
            "ORDER BY id DESC LIMIT 50",
            (category, tool),
        ).fetchall()
    if not rows:
        return 0.5
    return sum(r[0] for r in rows) / len(rows)


def rank_tools(tools: list, categories: set[str]) -> list:
    """Stable-sort tools by best success score across the active categories."""
    cat_list = list(categories) or ["any"]

    def score(t):
        name = getattr(t, "name", str(t))
        return max(tool_score(c, name) for c in cat_list)

    return sorted(tools, key=score, reverse=True)


def stats() -> list[dict]:
    """Aggregate stats per (category, tool)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT category, tool, COUNT(*) c, "
            "SUM(success) ok, MAX(ts) last "
            "FROM tool_outcomes GROUP BY category, tool ORDER BY c DESC LIMIT 200"
        ).fetchall()
    return [
        {
            "category": r[0],
            "tool": r[1],
            "calls": r[2],
            "successes": r[3],
            "rate": round((r[3] / r[2]) * 100, 1) if r[2] else 0,
            "last_used": r[4],
        }
        for r in rows
    ]
