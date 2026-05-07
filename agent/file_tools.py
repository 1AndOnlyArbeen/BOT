"""File operations scoped to the workspace folder. Safe for the agent to call."""
from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.tools import tool

from agent.backup import snapshot, undo_last, history
from agent.artifacts import set_last_written
from config import WORKSPACE_DIR, CODE_EXTENSIONS


def _resolve(rel_path: str) -> Path:
    """Resolve a workspace-relative path. Refuses to escape the workspace."""
    rel = Path(rel_path.lstrip("/"))
    full = (WORKSPACE_DIR / rel).resolve()
    if not str(full).startswith(str(WORKSPACE_DIR.resolve())):
        raise ValueError("path escapes workspace")
    return full


@tool
def list_files(path: str = ".") -> str:
    """List files and folders in the workspace. Use '.' for root."""
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"[error] {e}"
    if not target.exists():
        return f"[error] {path} not found"
    if target.is_file():
        return f"{target.name} ({target.stat().st_size} bytes)"

    out = []
    for p in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name)):
        rel = p.relative_to(WORKSPACE_DIR)
        if p.is_dir():
            out.append(f"📁 {rel}/")
        else:
            out.append(f"📄 {rel} ({p.stat().st_size}B)")
    return "\n".join(out) if out else "(empty)"


@tool
def read_file(path: str) -> str:
    """Read a file from the workspace. Returns content with line numbers."""
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"[error] {e}"
    if not target.exists():
        return f"[error] {path} not found"
    if not target.is_file():
        return f"[error] {path} is not a file"
    if target.stat().st_size > 200_000:
        return f"[error] file too large ({target.stat().st_size} bytes)"

    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"[error] {path} is not text"

    lines = text.split("\n")
    return "\n".join(f"{i+1:4} | {line}" for i, line in enumerate(lines))


@tool
def write_file(path: str, content: str) -> str:
    """Create or overwrite a file in the workspace. Creates parent dirs as needed. Auto-backs-up the previous version (use undo_last_edit to restore)."""
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"[error] {e}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        snapshot(target, op="write")
    target.write_text(content, encoding="utf-8")
    set_last_written(target)
    return f"✓ wrote {path} ({len(content)} chars)"


@tool
def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace exact `old_string` with `new_string` in a workspace file. old_string must appear exactly once."""
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"[error] {e}"
    if not target.exists():
        return f"[error] {path} not found"

    text = target.read_text(encoding="utf-8")
    count = text.count(old_string)
    if count == 0:
        return f"[error] old_string not found in {path}"
    if count > 1:
        return f"[error] old_string appears {count} times — make it unique"

    snapshot(target, op="edit")
    new_text = text.replace(old_string, new_string, 1)
    target.write_text(new_text, encoding="utf-8")
    set_last_written(target)
    return f"✓ edited {path}"


@tool
def run_python_file(path: str) -> str:
    """Run a Python file from the workspace with a 30s timeout. Returns stdout/stderr."""
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"[error] {e}"
    if not target.exists():
        return f"[error] {path} not found"
    if target.suffix != ".py":
        return f"[error] not a .py file"

    try:
        result = subprocess.run(
            ["python3", str(target)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(WORKSPACE_DIR),
        )
    except subprocess.TimeoutExpired:
        return "[timeout] killed after 30s"
    except Exception as e:
        return f"[error] {e}"

    out = (result.stdout or "")[-3000:]
    err = (result.stderr or "")[-1500:]
    parts = []
    if out:
        parts.append(f"--- stdout ---\n{out}")
    if err:
        parts.append(f"--- stderr ---\n{err}")
    parts.append(f"(exit {result.returncode})")
    return "\n".join(parts)


@tool
def delete_file(path: str) -> str:
    """Delete a file from the workspace. Use with care."""
    try:
        target = _resolve(path)
    except ValueError as e:
        return f"[error] {e}"
    if not target.exists():
        return f"[error] {path} not found"
    if target.is_dir():
        return f"[error] {path} is a directory; refusing"
    snapshot(target, op="delete")
    target.unlink()
    return f"✓ deleted {path} (backup saved — use undo_last_edit)"


@tool
def undo_last_edit(path: str = "") -> str:
    """Undo the last write/edit/delete to a file in the workspace. path: optional, restores last edit to that file specifically."""
    if path:
        try:
            target = _resolve(path)
        except ValueError as e:
            return f"[error] {e}"
        return undo_last(original_path=str(target))
    return undo_last()


@tool
def list_backups(path: str = "") -> str:
    """List recent file backups. path: optional filter to one file."""
    target = None
    if path:
        try:
            target = str(_resolve(path))
        except ValueError as e:
            return f"[error] {e}"
    rows = history(original_path=target, limit=20)
    if not rows:
        return "(no backups)"
    import datetime
    return "\n".join(
        f"{datetime.datetime.fromtimestamp(r['ts']/1000).strftime('%Y-%m-%d %H:%M:%S')}  "
        f"[{r['op']}]  {Path(r['original']).name}  ←  {Path(r['backup']).name}"
        for r in rows
    )


FILE_TOOLS = [
    list_files, read_file, write_file, edit_file,
    run_python_file, delete_file,
    undo_last_edit, list_backups,
]


def list_workspace_tree(max_depth: int = 3) -> list[tuple[str, bool]]:
    """Return [(relative_path, is_dir), ...] for UI rendering."""
    out = []

    def walk(d: Path, depth: int):
        if depth > max_depth:
            return
        for p in sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name)):
            if p.name.startswith(".") or p.name == "__pycache__":
                continue
            rel = p.relative_to(WORKSPACE_DIR)
            out.append((str(rel), p.is_dir()))
            if p.is_dir():
                walk(p, depth + 1)

    walk(WORKSPACE_DIR, 1)
    return out
