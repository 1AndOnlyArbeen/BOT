"""Saved macros: named workflows the user can run as a single command."""
from __future__ import annotations

import json
import time
from pathlib import Path

from config import DATA_DIR


MACROS_DIR = DATA_DIR / "macros"
MACROS_DIR.mkdir(parents=True, exist_ok=True)


def _path(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in "_-").lower()
    return MACROS_DIR / f"{safe}.json"


def save_macro(name: str, prompt: str, description: str = "") -> dict:
    p = _path(name)
    data = {
        "name": name,
        "prompt": prompt,
        "description": description,
        "created_at": time.time(),
        "runs": 0,
    }
    if p.exists():
        existing = json.loads(p.read_text())
        data["runs"] = existing.get("runs", 0)
        data["created_at"] = existing.get("created_at", time.time())
    p.write_text(json.dumps(data, indent=2))
    return data


def get_macro(name: str) -> dict | None:
    p = _path(name)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def delete_macro(name: str) -> bool:
    p = _path(name)
    if p.exists():
        p.unlink()
        return True
    return False


def list_macros() -> list[dict]:
    out = []
    for p in MACROS_DIR.glob("*.json"):
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            continue
    return sorted(out, key=lambda m: m.get("runs", 0), reverse=True)


def increment_run(name: str) -> None:
    p = _path(name)
    if not p.exists():
        return
    data = json.loads(p.read_text())
    data["runs"] = data.get("runs", 0) + 1
    data["last_run"] = time.time()
    p.write_text(json.dumps(data, indent=2))
