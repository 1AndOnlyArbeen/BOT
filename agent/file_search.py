"""File system search across the user's home directory."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from langchain_core.tools import tool


HOME = Path.home()


@tool
def find_files(name: str, path: str = "~") -> str:
    """Find files matching a name pattern. path defaults to home. Returns up to 30 matches."""
    base = Path(path).expanduser().resolve()
    if not base.exists():
        return f"[error] {path} not found"
    if shutil.which("fd"):
        cmd = ["fd", "--max-results", "30", "-H", "-t", "f", name, str(base)]
    else:
        cmd = ["find", str(base), "-maxdepth", "8", "-iname", f"*{name}*", "-type", "f"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        lines = [l for l in r.stdout.split("\n") if l.strip()][:30]
        return "\n".join(lines) or "(no matches)"
    except subprocess.TimeoutExpired:
        return "[timeout]"


@tool
def grep_files(pattern: str, path: str = "~", file_glob: str = "*") -> str:
    """Search file CONTENTS for a pattern. path: directory; file_glob: e.g. '*.py'. Returns top 40 matches."""
    base = Path(path).expanduser().resolve()
    if not base.exists():
        return f"[error] {path} not found"
    if shutil.which("rg"):
        cmd = ["rg", "--max-count", "3", "-n", "-S", "-g", file_glob, pattern, str(base)]
    else:
        cmd = [
            "grep", "-rIn",
            "--include", file_glob,
            "--max-count=3", pattern, str(base),
        ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = [l for l in r.stdout.split("\n") if l.strip()][:40]
        return "\n".join(lines) or "(no matches)"
    except subprocess.TimeoutExpired:
        return "[timeout]"


@tool
def file_info(path: str) -> str:
    """Get size, type, modified time of a file."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    s = p.stat()
    import datetime
    return (
        f"path: {p}\n"
        f"type: {'dir' if p.is_dir() else 'file'}\n"
        f"size: {s.st_size} bytes\n"
        f"modified: {datetime.datetime.fromtimestamp(s.st_mtime).isoformat(timespec='seconds')}"
    )


@tool
def recent_files(path: str = "~", count: int = 15) -> str:
    """List the most recently modified files under path."""
    base = Path(path).expanduser().resolve()
    if not base.exists():
        return f"[error] {path} not found"
    items = []
    for p in base.rglob("*"):
        try:
            if p.is_file() and not any(part.startswith(".") for part in p.parts[len(base.parts):]):
                items.append((p.stat().st_mtime, p))
        except (PermissionError, OSError):
            continue
        if len(items) > 5000:
            break
    items.sort(reverse=True)
    import datetime
    out = [
        f"{datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M')}  {p}"
        for t, p in items[:count]
    ]
    return "\n".join(out) or "(none)"


@tool
def list_dir(path: str = "~") -> str:
    """List contents of a directory."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    if not p.is_dir():
        return f"[error] {path} is a file"
    out = []
    for item in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name)):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            out.append(f"📁 {item.name}/")
        else:
            try:
                size = item.stat().st_size
                out.append(f"📄 {item.name} ({size}B)")
            except OSError:
                out.append(f"📄 {item.name}")
    return "\n".join(out) or "(empty)"


FILE_SEARCH_TOOLS = [find_files, grep_files, file_info, recent_files, list_dir]
