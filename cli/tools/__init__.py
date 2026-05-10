"""Curated tool registry for coder mode.

The legacy CODER_TOOLS list in agent/tools.py drags in 80+ tools (browser
automation, music control, video tools, vision LLM, etc.). For a focused
coding CLI we want a tight set the model can actually keep in its head.

This module composes a smaller, deterministic toolset by re-exporting the
proven workspace-scoped primitives plus our new project-aware tools.
"""
from __future__ import annotations

from typing import Any

from agent.file_tools import (
    list_files, read_file, write_file, edit_file, make_folder,
    run_python_file, delete_file, undo_last_edit, list_backups,
)
from agent.file_search import find_files, grep_files, file_info, list_dir
from agent.shell_tools import shell_exec
from agent.codebase_tools import (
    codebase_search, codebase_list_repos, codebase_list_files,
    codebase_show_file, codebase_explain_how_to,
)
from agent.code_library import save_code_pattern, search_code_library
from agent.git_tools import git_status, git_add, git_commit, git_diff, git_log
from agent.tools import web_search, python_exec, calculator
from agent.artifacts import save_artifact, recall_artifact, list_artifacts

from cli.tools.project import (
    project_info, read_project_notes, update_project_notes,
)
from cli.tools.tasks import list_tasks, add_task, complete_task, delete_task
from cli.tools.packages import (
    list_dependencies, install_package, uninstall_package, sync_packages,
)


# Order matters loosely — tools earlier in the list are listed first in the
# model's tool catalogue, which nudges it toward them. Lead with the
# project-orientation tools so the model checks them before guessing.

CODER_TOOLS: list[Any] = [
    # Project orientation
    project_info,
    read_project_notes,
    update_project_notes,

    # Persistent todo
    list_tasks,
    add_task,
    complete_task,
    delete_task,

    # Packages — read manifests + install/sync via the right manager
    list_dependencies,
    install_package,
    uninstall_package,
    sync_packages,

    # Filesystem (workspace-scoped, line-numbered reads)
    list_files,
    read_file,
    write_file,
    edit_file,
    make_folder,
    delete_file,
    undo_last_edit,
    list_backups,

    # Search across the workspace + home dir
    find_files,
    grep_files,
    file_info,
    list_dir,

    # Indexed code RAG (only useful if the user has ingested a codebase)
    codebase_search,
    codebase_explain_how_to,
    codebase_show_file,
    codebase_list_repos,
    codebase_list_files,

    # Pattern library (saved snippets from past wins)
    search_code_library,
    save_code_pattern,

    # Artifact registry (alias → workspace path)
    save_artifact,
    recall_artifact,
    list_artifacts,

    # Execution
    shell_exec,
    run_python_file,
    python_exec,

    # Git
    git_status,
    git_add,
    git_commit,
    git_diff,
    git_log,

    # Knowledge fallbacks
    web_search,
    calculator,
]


def tool_names() -> list[str]:
    """Return the list of tool names in registration order — useful for the prompt."""
    return [getattr(t, "name", str(t)) for t in CODER_TOOLS]
