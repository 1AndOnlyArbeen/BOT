"""Persistent todo list — survives across coder turns.

Stored as `.ultron/tasks.json` at the workspace root. Plain JSON so it's
hand-editable, git-friendly, and easy to inspect. The model can list,
add, complete, and remove tasks via tools; the system prompt also pins
the open list at the top so the model never forgets.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from cli.project.detect import project_profile

TASKS_DIRNAME = ".ultron"
TASKS_FILENAME = "tasks.json"
MAX_TASKS = 100


@dataclass
class TaskItem:
    id: int
    text: str
    status: str = "open"  # open | done
    created_at: float = field(default_factory=lambda: time.time())
    completed_at: float | None = None


def _tasks_path() -> Path:
    p = project_profile()
    return p.root / TASKS_DIRNAME / TASKS_FILENAME


def _load() -> list[TaskItem]:
    path = _tasks_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = []
    for r in raw or []:
        try:
            items.append(TaskItem(**r))
        except Exception:
            continue
    return items


def _save(items: list[TaskItem]) -> None:
    path = _tasks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps([asdict(t) for t in items], indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _next_id(items: list[TaskItem]) -> int:
    return max((t.id for t in items), default=0) + 1


# --- Public API used by tools and the prompt builder ----------------------

def list_open() -> list[TaskItem]:
    return [t for t in _load() if t.status == "open"]


def list_all() -> list[TaskItem]:
    return _load()


def add(text: str) -> TaskItem:
    text = (text or "").strip()
    if not text:
        raise ValueError("task text is required")
    items = _load()
    if len(items) >= MAX_TASKS:
        # Roll over: drop oldest done tasks.
        items = [t for t in items if t.status == "open"][-MAX_TASKS + 1:]
    item = TaskItem(id=_next_id(items), text=text)
    items.append(item)
    _save(items)
    return item


def complete(task_id: int) -> TaskItem | None:
    items = _load()
    for t in items:
        if t.id == task_id and t.status == "open":
            t.status = "done"
            t.completed_at = time.time()
            _save(items)
            return t
    return None


def delete(task_id: int) -> bool:
    items = _load()
    new_items = [t for t in items if t.id != task_id]
    if len(new_items) == len(items):
        return False
    _save(new_items)
    return True


def reset() -> int:
    items = _load()
    _save([])
    return len(items)


def open_block(max_items: int = 8) -> str:
    """Return a system-prompt-ready block listing open tasks."""
    items = list_open()[:max_items]
    if not items:
        return ""
    lines = "\n".join(f"  - [#{t.id}] {t.text}" for t in items)
    return (
        "\n\n# Open tasks (your persistent todo list — call complete_task when done)\n"
        f"{lines}\n"
    )
