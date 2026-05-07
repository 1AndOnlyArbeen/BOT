"""Development helpers: pip/apt search & info, code formatters, env info."""
from __future__ import annotations

import shutil
import subprocess
import sys

from langchain_core.tools import tool


def _have(c: str) -> bool:
    return shutil.which(c) is not None


@tool
def pip_search(package: str) -> str:
    """Look up a Python package on PyPI."""
    try:
        import requests
        r = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=10)
        if r.status_code != 200:
            return f"not found: {package}"
        info = r.json()["info"]
        return (
            f"{info['name']} {info['version']}\n"
            f"{info.get('summary', '')}\n"
            f"home: {info.get('home_page', '')}\n"
            f"requires Python: {info.get('requires_python', 'any')}"
        )
    except Exception as e:
        return f"[error] {e}"


@tool
def pip_installed(package: str = "") -> str:
    """Check if a Python package is installed (or list all if empty)."""
    cmd = [sys.executable, "-m", "pip", "show" if package else "list"]
    if package:
        cmd.append(package)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout.strip()[:3000] if r.returncode == 0 else f"not installed: {package}"
    except Exception as e:
        return f"[error] {e}"


@tool
def apt_search(package: str) -> str:
    """Search apt repositories for a package."""
    if not _have("apt-cache"):
        return "[error] apt-cache not available"
    try:
        r = subprocess.run(
            ["apt-cache", "search", package],
            capture_output=True, text=True, timeout=15,
        )
        lines = r.stdout.split("\n")[:20]
        return "\n".join(lines) or f"no results for {package}"
    except Exception as e:
        return f"[error] {e}"


@tool
def apt_show(package: str) -> str:
    """Show details about an apt package."""
    if not _have("apt-cache"):
        return "[error] apt-cache not available"
    try:
        r = subprocess.run(
            ["apt-cache", "show", package],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout[:1500] or f"no info for {package}"
    except Exception as e:
        return f"[error] {e}"


@tool
def env_info() -> str:
    """Report dev environment: python, node, etc."""
    items = []
    for cmd, args in (
        ("python3", ["--version"]),
        ("pip", ["--version"]),
        ("node", ["--version"]),
        ("npm", ["--version"]),
        ("git", ["--version"]),
        ("docker", ["--version"]),
        ("ollama", ["--version"]),
    ):
        if _have(cmd):
            try:
                r = subprocess.run([cmd, *args], capture_output=True, text=True, timeout=5)
                items.append(f"{cmd}: {(r.stdout or r.stderr).strip().splitlines()[0]}")
            except Exception:
                pass
        else:
            items.append(f"{cmd}: (not installed)")
    return "\n".join(items)


@tool
def format_python(code: str) -> str:
    """Format Python code with black (if installed)."""
    if not _have("black"):
        return "[error] pip install black"
    try:
        r = subprocess.run(
            ["black", "-q", "-"],
            input=code, text=True,
            capture_output=True, timeout=15,
        )
        return r.stdout if r.returncode == 0 else r.stderr
    except Exception as e:
        return f"[error] {e}"


DEV_TOOLS = [pip_search, pip_installed, apt_search, apt_show, env_info, format_python]
