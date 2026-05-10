"""Tools for the persistent todo list (cli/tasks.py)."""
from __future__ import annotations

from langchain_core.tools import tool

from cli import tasks as _tasks


@tool("list_tasks")
def list_tasks() -> str:
    """List the persistent todo items for THIS workspace (open + done).

    Persists across chat sessions in .ultron/tasks.json. Use this to remember
    what's still pending before starting new work.
    """
    items = _tasks.list_all()
    if not items:
        return "(no tasks yet)"
    lines = []
    for t in items:
        marker = "✓" if t.status == "done" else "·"
        lines.append(f"  {marker} [#{t.id}] {t.text}")
    return "\n".join(lines)


@tool("add_task")
def add_task(text: str) -> str:
    """Add a task to the persistent todo list at the workspace root.

    Use this when the user says "remind me to…", "add a TODO for…", or
    when YOU find work that's worth doing later but isn't this turn's
    focus. Keep the text short and actionable.
    """
    try:
        item = _tasks.add(text)
    except ValueError as e:
        return f"[add_task] {e}"
    return f"✓ added task #{item.id}: {item.text}"


@tool("complete_task")
def complete_task(task_id: int) -> str:
    """Mark a task as done. Pass the task id (the integer in `#42` format)."""
    item = _tasks.complete(int(task_id))
    if item is None:
        return f"[complete_task] no open task with id={task_id}"
    return f"✓ completed task #{item.id}: {item.text}"


@tool("delete_task")
def delete_task(task_id: int) -> str:
    """Remove a task entirely (open or done). Use sparingly — prefer complete_task."""
    if _tasks.delete(int(task_id)):
        return f"✓ deleted task #{task_id}"
    return f"[delete_task] no task with id={task_id}"
