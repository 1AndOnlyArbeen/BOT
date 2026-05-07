"""Calendar + tasks: taskwarrior integration + simple ICS reading + native task DB."""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

from config import DATA_DIR


TASKS_DB = DATA_DIR / "tasks.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due REAL,
    project TEXT,
    priority TEXT,
    status TEXT DEFAULT 'open',
    created_at REAL NOT NULL
);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(TASKS_DB)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init():
    with _conn() as c:
        c.executescript(SCHEMA)


_init()


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _parse_when(s: str) -> float | None:
    s = s.strip().lower()
    if not s:
        return None
    parts = s.split()
    if len(parts) == 2 and parts[0].lstrip("-").replace(".", "", 1).isdigit():
        n = float(parts[0])
        unit = parts[1].rstrip("s")
        mult = {"sec": 1, "min": 60, "hr": 3600, "hour": 3600, "day": 86400, "week": 604800}.get(unit)
        if mult:
            return time.time() + n * mult
    if s == "today":
        return datetime.now().replace(hour=23, minute=59).timestamp()
    if s == "tomorrow":
        return datetime.now().replace(hour=23, minute=59).timestamp() + 86400
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%H:%M":
                today = datetime.now().replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
                if today.timestamp() < time.time():
                    today = today.replace(day=today.day + 1)
                return today.timestamp()
            return dt.timestamp()
        except ValueError:
            continue
    return None


@tool
def add_task(title: str, due: str = "", project: str = "", priority: str = "") -> str:
    """Add a task. due: '5 min', 'tomorrow', '2026-05-08 14:00'. priority: H, M, L."""
    due_ts = _parse_when(due) if due else None
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO tasks(title, due, project, priority, created_at) VALUES (?,?,?,?,?)",
            (title, due_ts, project or None, priority or None, time.time()),
        )
    return f"✓ task #{cur.lastrowid}: {title}"


@tool
def list_tasks(status: str = "open", project: str = "") -> str:
    """List tasks. status: open, done, all. project: optional filter."""
    q = "SELECT id, title, due, project, priority, status FROM tasks"
    where = []
    args = []
    if status != "all":
        where.append("status=?")
        args.append(status)
    if project:
        where.append("project=?")
        args.append(project)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY (due IS NULL), due ASC LIMIT 50"
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    if not rows:
        return "(no tasks)"
    out = []
    for r in rows:
        due_str = datetime.fromtimestamp(r[2]).strftime("%Y-%m-%d %H:%M") if r[2] else "—"
        prio = f" [{r[4]}]" if r[4] else ""
        proj = f" #{r[3]}" if r[3] else ""
        out.append(f"#{r[0]} {r[1]}{prio}{proj}  ({due_str})  [{r[5]}]")
    return "\n".join(out)


@tool
def complete_task(task_id: int) -> str:
    """Mark task done."""
    with _conn() as c:
        c.execute("UPDATE tasks SET status='done' WHERE id=?", (int(task_id),))
    return f"✓ done #{task_id}"


@tool
def delete_task(task_id: int) -> str:
    """Delete a task."""
    with _conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (int(task_id),))
    return f"✓ deleted #{task_id}"


@tool
def taskwarrior_sync() -> str:
    """If 'task' CLI is installed, list tasks from taskwarrior."""
    if not _have("task"):
        return "[info] taskwarrior not installed"
    try:
        r = subprocess.run(
            ["task", "list"],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout[:2000] or "(no taskwarrior tasks)"
    except Exception as e:
        return f"[error] {e}"


@tool
def read_ics(path: str) -> str:
    """Read events from an ICS calendar file."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[error] {e}"
    events = []
    cur = {}
    for line in text.split("\n"):
        line = line.strip()
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur.get("SUMMARY"):
                events.append(cur)
            cur = {}
        elif ":" in line and cur is not None:
            k, _, v = line.partition(":")
            k = k.split(";")[0]
            cur[k] = v
    if not events:
        return "(no events)"
    out = []
    for e in events[:30]:
        out.append(f"{e.get('DTSTART','?')}  {e.get('SUMMARY','?')}  {e.get('LOCATION','')}")
    return "\n".join(out)


CALENDAR_TOOLS = [add_task, list_tasks, complete_task, delete_task, taskwarrior_sync, read_ics]
