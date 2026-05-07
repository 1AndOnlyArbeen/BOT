"""Calendar / tasks API."""
from __future__ import annotations

import sqlite3
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.calendar_tools import _conn, _parse_when

router = APIRouter()


class CreateTask(BaseModel):
    title: str
    due: str = ""
    project: str = ""
    priority: str = ""


@router.get("/tasks")
def tasks(status: str = "open", project: str = "") -> list[dict]:
    q = "SELECT id, title, due, project, priority, status, created_at FROM tasks"
    where, args = [], []
    if status != "all":
        where.append("status=?"); args.append(status)
    if project:
        where.append("project=?"); args.append(project)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY (due IS NULL), due ASC LIMIT 200"
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    return [
        {
            "id": r[0], "title": r[1], "due": r[2],
            "project": r[3], "priority": r[4], "status": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]


@router.post("/tasks")
def create(body: CreateTask) -> dict:
    due_ts = _parse_when(body.due) if body.due else None
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO tasks(title, due, project, priority, created_at) VALUES (?,?,?,?,?)",
            (body.title, due_ts, body.project or None, body.priority or None, time.time()),
        )
    return {"id": cur.lastrowid}


@router.patch("/tasks/{task_id}")
def update(task_id: int, status: str | None = None) -> dict:
    if status:
        with _conn() as c:
            c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    return {"ok": True}


@router.delete("/tasks/{task_id}")
def delete(task_id: int) -> dict:
    with _conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    return {"ok": True}
