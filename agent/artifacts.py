"""Artifact registry — name workspace files so they can be recalled later.

Storage: JSON at data/artifacts.json. Lives in the repo (data/ itself is not
gitignored — only specific subpaths are), so artifact aliases travel with
`git push`/`git pull`. The actual files live in workspace/ which is also
committed.

Why JSON not SQLite: registry is small, append-mostly, and human-readable
makes git diffs sane when the user merges across machines.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from langchain_core.tools import tool

from config import DATA_DIR, WORKSPACE_DIR


_REGISTRY_PATH = DATA_DIR / "artifacts.json"
_LOCK = threading.Lock()
_LAST_WRITTEN: Path | None = None


def _load() -> dict:
    if not _REGISTRY_PATH.exists():
        return {"artifacts": {}}
    try:
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"artifacts": {}}


def _save(data: dict) -> None:
    _REGISTRY_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def set_last_written(path: Path | str | None) -> None:
    """Called by file_tools.write_file after a successful write.

    Pass None to reset (e.g. at the start of a new agent turn) so verifiers
    don't act on stale state from a previous turn.
    """
    global _LAST_WRITTEN
    _LAST_WRITTEN = Path(path) if path is not None else None


def get_last_written() -> Path | None:
    return _LAST_WRITTEN


def _normalize_alias(alias: str) -> str:
    return alias.strip().lower().replace(" ", "-")


def _summarize(content: str, max_len: int = 120) -> str:
    """First non-empty line of the file, trimmed — used for list views."""
    for line in content.splitlines():
        s = line.strip().lstrip("#").lstrip("//").strip()
        if s:
            return s[:max_len]
    return f"({len(content)} chars)"


def register(alias: str, rel_path: str, content: str) -> dict:
    """Add or update an alias → workspace-relative path mapping. Returns the new record."""
    norm = _normalize_alias(alias)
    if not norm:
        raise ValueError("alias is empty")
    record = {
        "alias": norm,
        "path": rel_path,
        "size": len(content),
        "sha256": hashlib.sha256(content.encode("utf-8", "replace")).hexdigest()[:16],
        "summary": _summarize(content),
        "saved_at": int(time.time()),
    }
    with _LOCK:
        data = _load()
        data.setdefault("artifacts", {})[norm] = record
        _save(data)
    return record


def get_by_alias(alias: str) -> dict | None:
    norm = _normalize_alias(alias)
    return _load().get("artifacts", {}).get(norm)


def find_fuzzy(query: str, limit: int = 5) -> list[dict]:
    """Substring match against alias + summary. Cheap; good enough for a small registry."""
    q = query.strip().lower()
    if not q:
        return []
    matches = []
    for record in _load().get("artifacts", {}).values():
        haystack = f"{record.get('alias','')} {record.get('summary','')} {record.get('path','')}".lower()
        if q in haystack:
            matches.append(record)
    matches.sort(key=lambda r: r.get("saved_at", 0), reverse=True)
    return matches[:limit]


def list_all() -> list[dict]:
    records = list(_load().get("artifacts", {}).values())
    records.sort(key=lambda r: r.get("saved_at", 0), reverse=True)
    return records


def remove(alias: str) -> bool:
    norm = _normalize_alias(alias)
    with _LOCK:
        data = _load()
        if norm in data.get("artifacts", {}):
            del data["artifacts"][norm]
            _save(data)
            return True
    return False


def _resolve_workspace_path(rel_path: str) -> Path:
    rel = Path(rel_path.lstrip("/"))
    full = (WORKSPACE_DIR / rel).resolve()
    if not str(full).startswith(str(WORKSPACE_DIR.resolve())):
        raise ValueError("path escapes workspace")
    return full


@tool
def save_artifact(alias: str, path: str = "") -> str:
    """Pin a name to a workspace file so it can be recalled later by alias.

    Use when the user says: "save this as X", "save it as X", "remember this code as X".

    alias: short identifier (e.g. "todo-app", "voice-config"). Spaces become dashes.
    path: workspace-relative path. Leave empty to use the most recently written file.
    """
    if not alias.strip():
        return "[save_artifact] alias required"

    target_rel: str
    if path.strip():
        target_rel = path.strip().lstrip("/")
    else:
        last = get_last_written()
        if last is None:
            return "[save_artifact] no recent write — provide path explicitly"
        try:
            target_rel = str(last.relative_to(WORKSPACE_DIR.resolve()))
        except ValueError:
            return "[save_artifact] last-written file is outside workspace"

    try:
        full = _resolve_workspace_path(target_rel)
    except ValueError as e:
        return f"[save_artifact] {e}"
    if not full.exists() or not full.is_file():
        return f"[save_artifact] {target_rel} not found"

    try:
        content = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = ""

    record = register(alias, target_rel, content)
    return f"✓ saved '{record['alias']}' → {record['path']} ({record['size']} chars)"


@tool
def recall_artifact(query: str) -> str:
    """Recall a saved artifact by alias or fuzzy match. Returns path + full file content.

    Use when the user says: "give me X again", "recall X", "show me the X I saved",
    "pull up the X", "get that X back".
    """
    if not query.strip():
        return "[recall_artifact] need an alias or search term"

    record = get_by_alias(query)
    if record is None:
        candidates = find_fuzzy(query)
        if not candidates:
            return f"[recall_artifact] no artifact matching '{query}'. Use list_artifacts to see all."
        if len(candidates) > 1:
            preview = "\n".join(f"  · {c['alias']} → {c['path']}" for c in candidates[:5])
            return f"[recall_artifact] multiple matches for '{query}':\n{preview}\nCall again with the exact alias."
        record = candidates[0]

    try:
        full = _resolve_workspace_path(record["path"])
    except ValueError as e:
        return f"[recall_artifact] {e}"
    if not full.exists():
        return f"[recall_artifact] alias '{record['alias']}' points to {record['path']} but the file is gone"

    try:
        content = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"[recall_artifact] {record['path']} is not text"

    return f"# artifact: {record['alias']}\n# path: {record['path']}\n# saved: {time.strftime('%Y-%m-%d %H:%M', time.localtime(record.get('saved_at', 0)))}\n\n{content}"


@tool
def list_artifacts() -> str:
    """List every saved artifact (alias, path, when saved, one-line summary)."""
    records = list_all()
    if not records:
        return "(no artifacts saved yet — use save_artifact to pin one)"
    lines = []
    for r in records:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("saved_at", 0)))
        lines.append(f"· {r['alias']:24}  {r['path']:40}  {when}  — {r.get('summary','')[:60]}")
    return "\n".join(lines)


ARTIFACT_TOOLS = [save_artifact, recall_artifact, list_artifacts]
