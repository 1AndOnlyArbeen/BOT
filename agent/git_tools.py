"""Git operations on the workspace folder."""
from __future__ import annotations

import shutil
import subprocess

from langchain_core.tools import tool

from config import WORKSPACE_DIR


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _git(*args: str, timeout: int = 30) -> str:
    if not _have("git"):
        return "[error] git not installed"
    try:
        r = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(WORKSPACE_DIR),
        )
        out = r.stdout.strip()
        err = r.stderr.strip()
        if r.returncode != 0:
            return f"[error] {err or out}"
        return out or err or "(ok)"
    except subprocess.TimeoutExpired:
        return "[timeout]"


@tool
def git_status() -> str:
    """Show working tree status of the workspace."""
    return _git("status", "-sb")


@tool
def git_diff(path: str = "") -> str:
    """Show unstaged diff. path: optional file."""
    if path:
        return _git("diff", "--", path)[:6000]
    return _git("diff")[:6000]


@tool
def git_log(count: int = 10) -> str:
    """Show recent commits."""
    return _git("log", f"-n{count}", "--oneline", "--decorate")


@tool
def git_init() -> str:
    """Initialize a git repository in the workspace."""
    return _git("init")


@tool
def git_add(paths: str = ".") -> str:
    """Stage files. paths: space-separated, default '.' (all)."""
    parts = paths.split() if paths else ["."]
    return _git("add", *parts)


@tool
def git_commit(message: str) -> str:
    """Commit staged changes."""
    return _git("commit", "-m", message)


@tool
def git_branch() -> str:
    """List branches."""
    return _git("branch", "-a")


@tool
def git_checkout(branch: str, create: bool = False) -> str:
    """Switch branches. create=True to make a new branch."""
    args = ["checkout"] + (["-b"] if create else []) + [branch]
    return _git(*args)


GIT_TOOLS = [
    git_status, git_diff, git_log, git_init,
    git_add, git_commit, git_branch, git_checkout,
]
