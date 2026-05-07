"""GitHub via the `gh` CLI. Requires `gh auth login` once."""
from __future__ import annotations

import json
import shutil
import subprocess

from langchain_core.tools import tool


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _gh(*args: str, json_fields: str | None = None) -> str:
    if not _have("gh"):
        return "[error] gh CLI not installed (https://cli.github.com)"
    cmd = ["gh", *args]
    if json_fields:
        cmd += ["--json", json_fields]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"[error] {e}"


@tool
def gh_list_repos(user: str = "") -> str:
    """List repos for a user (default: yours)."""
    if user:
        return _gh("repo", "list", user, "--limit", "30")
    return _gh("repo", "list", "--limit", "30")


@tool
def gh_list_issues(repo: str = "", state: str = "open") -> str:
    """List issues for a repo (e.g. 'owner/repo'). state: open/closed/all."""
    args = ["issue", "list", "--state", state, "--limit", "30"]
    if repo:
        args = ["issue", "list", "--repo", repo, "--state", state, "--limit", "30"]
    return _gh(*args)


@tool
def gh_create_issue(repo: str, title: str, body: str = "") -> str:
    """Create an issue. repo: 'owner/name'."""
    return _gh("issue", "create", "--repo", repo, "--title", title, "--body", body or " ")


@tool
def gh_list_prs(repo: str = "", state: str = "open") -> str:
    """List pull requests."""
    args = ["pr", "list", "--state", state, "--limit", "30"]
    if repo:
        args = ["pr", "list", "--repo", repo, "--state", state, "--limit", "30"]
    return _gh(*args)


@tool
def gh_pr_view(pr_number: int, repo: str = "") -> str:
    """View a PR's details."""
    args = ["pr", "view", str(pr_number)]
    if repo:
        args += ["--repo", repo]
    return _gh(*args)


@tool
def gh_pr_create(title: str, body: str = "", base: str = "main") -> str:
    """Open a PR from current branch to `base`. Run from inside a repo."""
    return _gh("pr", "create", "--title", title, "--body", body or " ", "--base", base)


@tool
def gh_workflow_runs(repo: str = "") -> str:
    """List recent workflow runs."""
    args = ["run", "list", "--limit", "20"]
    if repo:
        args += ["--repo", repo]
    return _gh(*args)


GITHUB_TOOLS = [
    gh_list_repos, gh_list_issues, gh_create_issue,
    gh_list_prs, gh_pr_view, gh_pr_create, gh_workflow_runs,
]
