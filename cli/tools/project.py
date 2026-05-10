"""Project-aware tools — surfaces ULTRON.md and the detected profile to the model."""
from __future__ import annotations

from langchain_core.tools import tool

from cli.project.detect import project_profile
from cli.project.notes import (
    NOTES_FILENAME,
    append_section as _append_section,
    notes_path,
    read_notes,
)


@tool("project_info")
def project_info() -> str:
    """Return a structured summary of the current project (languages, frameworks, package manager, key commands).

    Use this when the user asks "what is this project?", "what stack are we on?",
    or anything that needs you to orient yourself before doing real work. The
    answer is cheaper than reading a bunch of files yourself.
    """
    p = project_profile()
    lines = [
        f"Project: {p.name}",
        f"Workspace: {p.root}",
        f"Languages: {', '.join(p.languages) or 'unknown'}",
        f"Frameworks: {', '.join(p.frameworks) or '(none)'}",
        f"Package manager: {p.package_manager or 'n/a'}",
        f"Test command: {p.test_command or 'not detected'}",
        f"Build command: {p.build_command or 'not detected'}",
        f"Run command: {p.run_command or 'not detected'}",
        f"Detected manifests: {', '.join(p.detected_files) or '(none)'}",
        f"Git repo: {'yes' if p.is_git else 'no'}",
    ]
    return "\n".join(lines)


@tool("read_project_notes")
def read_project_notes() -> str:
    """Return the contents of ULTRON.md (the per-project memory file at the workspace root).

    Auto-creates the file with a default template the first time it's read.
    Always prefer information from this file over guessing.
    """
    p = project_profile()
    return read_notes(p) or f"({NOTES_FILENAME} is empty)"


@tool("update_project_notes")
def update_project_notes(heading: str, body: str) -> str:
    """Append a `## heading` section with the given body to ULTRON.md.

    Use this when the user teaches you a project convention worth remembering
    ("we always use 4-space indent", "tests live under tests/unit") or asks
    you to pin something. Heading must be short; body can span paragraphs.
    """
    p = project_profile()
    if not heading.strip():
        return "[update_project_notes] heading is required"
    _append_section(p, heading.strip(), body.strip())
    return f"Pinned in {notes_path(p).name} under '## {heading.strip()}'."
