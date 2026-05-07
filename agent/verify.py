"""Auto-verify code right after the model writes it.

Tier-1 reliability bump: instead of waiting for the user to discover a syntax
error, run a fast language-aware check on the just-written file and inject any
errors back into the next agent step. The model rarely fixes what it doesn't
see — surfacing the error makes the fix happen.

What this is NOT: a full test runner. We do *syntax* + *cheap static* checks
only (sub-second). Real test execution still happens via run_python_file /
shell_exec when the user asks for it.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


_EXT_LANG = {
    ".py":  "python",
    ".js":  "node",
    ".mjs": "node",
    ".cjs": "node",
    ".ts":  "typescript",
    ".tsx": "typescript",
    ".jsx": "node",
    ".json": "json",
    ".sh":  "bash",
}


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "")[-2000:], (r.stderr or "")[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "", f"[verify] timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", f"[verify] {e}"


def _verify_python(path: Path) -> str:
    """Compile + lazy lint. Returns '' if clean, else a short error report."""
    rc, _out, err = _run(["python3", "-m", "py_compile", str(path)], timeout=10)
    if rc != 0:
        return f"py_compile failed:\n{err.strip()}"
    if _have("pyflakes"):
        rc, out, err = _run(["pyflakes", str(path)], timeout=10)
        warnings = (out + err).strip()
        if warnings:
            return f"pyflakes warnings:\n{warnings}"
    return ""


def _verify_node(path: Path) -> str:
    """node --check parses without executing. Catches syntax errors fast."""
    if not _have("node"):
        return ""
    rc, _out, err = _run(["node", "--check", str(path)], timeout=8)
    if rc != 0:
        return f"node --check failed:\n{err.strip()}"
    return ""


def _verify_typescript(path: Path) -> str:
    """If tsc is around, do a lightweight no-emit check. Otherwise skip."""
    if not _have("tsc"):
        return ""
    rc, out, err = _run(["tsc", "--noEmit", "--allowJs", "--skipLibCheck", str(path)], timeout=15)
    if rc != 0:
        msg = (out + err).strip()
        return f"tsc errors:\n{msg[-1500:]}"
    return ""


def _verify_json(path: Path) -> str:
    import json
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return f"invalid JSON: {e}"
    return ""


def _verify_bash(path: Path) -> str:
    if not _have("bash"):
        return ""
    rc, _out, err = _run(["bash", "-n", str(path)], timeout=5)
    if rc != 0:
        return f"bash syntax error:\n{err.strip()}"
    return ""


def verify_file(path: Path | str) -> str:
    """Return '' if the file is clean, else a short error report (max ~2KB).

    Picks the right checker by extension. Unknown extensions return '' (we
    don't pretend to verify what we can't).
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    lang = _EXT_LANG.get(p.suffix.lower())
    if lang == "python":
        return _verify_python(p)
    if lang == "node":
        return _verify_node(p)
    if lang == "typescript":
        return _verify_typescript(p)
    if lang == "json":
        return _verify_json(p)
    if lang == "bash":
        return _verify_bash(p)
    return ""
