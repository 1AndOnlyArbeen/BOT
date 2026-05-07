"""Snapshot files before write/edit. Append-only history with atomic restore."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from config import DATA_DIR


BACKUP_ROOT = DATA_DIR / "backups"
INDEX = BACKUP_ROOT / "index.jsonl"
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)


def _record(entry: dict) -> None:
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def snapshot(target: Path, op: str = "write") -> str | None:
    """Copy `target` to backup with timestamp. Returns backup path or None."""
    if not target.exists() or not target.is_file():
        return None
    ts = int(time.time() * 1000)
    rel = target.name + f".{ts}.bak"
    dest = BACKUP_ROOT / rel
    shutil.copy2(target, dest)
    _record({
        "ts": ts,
        "original": str(target),
        "backup": str(dest),
        "op": op,
    })
    return str(dest)


def history(original_path: str | None = None, limit: int = 30) -> list[dict]:
    if not INDEX.exists():
        return []
    rows = []
    with INDEX.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if original_path and e.get("original") != original_path:
                continue
            rows.append(e)
    return rows[-limit:][::-1]


def undo_last(original_path: str | None = None) -> str:
    """Restore the most recent backup of a file (or any file if path omitted)."""
    rows = history(original_path=original_path, limit=1)
    if not rows:
        return "[error] no backup to restore"
    e = rows[0]
    src = Path(e["backup"])
    dst = Path(e["original"])
    if not src.exists():
        return f"[error] backup {src} missing"
    shutil.copy2(src, dst)
    return f"✓ restored {dst} from backup {src.name}"


def restore(backup_filename: str) -> str:
    """Restore a specific backup by filename."""
    rows = history(limit=10000)
    for e in rows:
        if Path(e["backup"]).name == backup_filename:
            src = Path(e["backup"])
            dst = Path(e["original"])
            shutil.copy2(src, dst)
            return f"✓ restored {dst}"
    return f"[error] backup {backup_filename} not found"
