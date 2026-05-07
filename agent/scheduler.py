"""In-process reminders + scheduled notifications. Persisted to SQLite."""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

from langchain_core.tools import tool

from config import DATA_DIR


SCHED_DB = DATA_DIR / "scheduler.db"
_thread = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT,
    fire_at REAL NOT NULL,
    fired INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(SCHED_DB)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init():
    with _conn() as c:
        c.executescript(SCHEMA)


_init()


def _fire(title: str, message: str):
    import shutil, subprocess
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "-u", "critical", title, message or ""])
    try:
        from voice.tts import speak_async
        speak_async(f"{title}. {message}" if message else title)
    except Exception:
        pass


def _scheduler_loop():
    while True:
        try:
            now = time.time()
            with _conn() as c:
                rows = c.execute(
                    "SELECT id, title, message FROM reminders WHERE fired=0 AND fire_at<=?",
                    (now,),
                ).fetchall()
            for rid, title, message in rows:
                _fire(title, message or "")
                with _conn() as c:
                    c.execute("UPDATE reminders SET fired=1 WHERE id=?", (rid,))
        except Exception:
            pass
        time.sleep(15)


def ensure_scheduler():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _thread.start()


ensure_scheduler()


def _parse_when(s: str) -> float | None:
    """Parse '5 min', '2 hours', '30 seconds', or 'YYYY-MM-DD HH:MM'."""
    s = s.strip().lower()
    parts = s.split()
    if len(parts) == 2 and parts[0].lstrip("-").replace(".", "", 1).isdigit():
        n = float(parts[0])
        unit = parts[1].rstrip("s")
        mult = {"sec": 1, "second": 1, "min": 60, "minute": 60, "hr": 3600, "hour": 3600, "day": 86400}.get(unit)
        if mult:
            return time.time() + n * mult
    if "in " in s:
        return _parse_when(s.replace("in ", "", 1))
    for fmt in ("%Y-%m-%d %H:%M", "%H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%H:%M":
                today = datetime.now().replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
                if today.timestamp() < time.time():
                    today += timedelta(days=1)
                return today.timestamp()
            return dt.timestamp()
        except ValueError:
            continue
    return None


@tool
def remind_me(when: str, title: str, message: str = "") -> str:
    """Set a reminder. when: '5 min', '2 hours', '15:30', '2026-05-07 14:00'.
    Fires desktop notification + spoken alert."""
    fire_at = _parse_when(when)
    if not fire_at:
        return f"[error] couldn't parse '{when}'. Try '5 min', '14:30', or 'YYYY-MM-DD HH:MM'"
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO reminders(title, message, fire_at, created_at) VALUES (?,?,?,?)",
            (title, message, fire_at, time.time()),
        )
    when_str = datetime.fromtimestamp(fire_at).strftime("%Y-%m-%d %H:%M:%S")
    return f"✓ reminder #{cur.lastrowid} set for {when_str}"


@tool
def list_reminders() -> str:
    """List all pending reminders."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, message, fire_at FROM reminders WHERE fired=0 ORDER BY fire_at"
        ).fetchall()
    if not rows:
        return "(none)"
    return "\n".join(
        f"#{r[0]} — {datetime.fromtimestamp(r[3]).strftime('%Y-%m-%d %H:%M')} — {r[1]}"
        + (f" ({r[2]})" if r[2] else "")
        for r in rows
    )


@tool
def cancel_reminder(reminder_id: int) -> str:
    """Cancel a pending reminder by ID."""
    with _conn() as c:
        c.execute("DELETE FROM reminders WHERE id=?", (int(reminder_id),))
    return f"✓ cancelled #{reminder_id}"


@tool
def current_time() -> str:
    """Get the current local time and date."""
    now = datetime.now()
    return now.strftime("%A, %Y-%m-%d %H:%M:%S")


SCHEDULER_TOOLS = [remind_me, list_reminders, cancel_reminder, current_time]
