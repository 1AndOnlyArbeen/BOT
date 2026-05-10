"""Folder + project primer.

Combines:
  - the detected project profile (languages, frameworks, commands)
  - the user-maintained ULTRON.md notes
  - a 2-level folder tree of the workspace

into a single block that prefixes the system prompt every coder turn. The
primer is what gives the model concrete grounding so it doesn't have to
spend tool calls just figuring out where it is.
"""
from __future__ import annotations

from pathlib import Path

from agent.file_tools import list_workspace_tree
from cli.project.detect import ProjectProfile
from cli.project.notes import read_notes


MAX_TREE_ENTRIES = 50


def _format_tree(profile: ProjectProfile, max_entries: int = MAX_TREE_ENTRIES) -> str:
    try:
        entries = list_workspace_tree(max_depth=2)
    except Exception:
        entries = []

    if not entries:
        return "(workspace is empty — file-tool paths are relative to this root)"

    lines: list[str] = []
    for rel, is_dir in entries[:max_entries]:
        depth = rel.count("/")
        indent = "  " * depth
        lines.append(f"{indent}{'📁 ' if is_dir else '📄 '}{rel}{'/' if is_dir else ''}")
    if len(entries) > max_entries:
        lines.append(f"  …(+{len(entries) - max_entries} more — call list_files to see all)")
    return "\n".join(lines)


def _format_profile(profile: ProjectProfile) -> str:
    bits = [f"- **Name**: `{profile.name}`"]
    if profile.languages:
        bits.append(f"- **Languages**: {', '.join(profile.languages)}")
    if profile.frameworks:
        bits.append(f"- **Frameworks**: {', '.join(profile.frameworks)}")
    if profile.package_manager:
        bits.append(f"- **Package manager**: `{profile.package_manager}`")
    if profile.test_command:
        bits.append(f"- **Test**: `{profile.test_command}`")
    if profile.build_command:
        bits.append(f"- **Build**: `{profile.build_command}`")
    if profile.run_command:
        bits.append(f"- **Run**: `{profile.run_command}`")
    if profile.detected_files:
        bits.append(f"- **Detected manifests**: {', '.join(profile.detected_files)}")
    bits.append(f"- **Git repo**: {'yes' if profile.is_git else 'no'}")
    return "\n".join(bits)


def build_primer(profile: ProjectProfile) -> str:
    """Return the full project-context block for system-prompt injection."""
    profile_block = _format_profile(profile)
    notes_block = read_notes(profile).strip()
    tree_block = _format_tree(profile)

    out = (
        "\n\n# Project context (refreshed every turn)\n"
        f"Workspace root: `{profile.root}`\n"
        "All file tools are scoped here — paths are relative to this root.\n\n"
        "## Profile\n"
        f"{profile_block}\n\n"
        "## Folder tree (depth 2)\n"
        f"{tree_block}\n"
    )

    try:
        from cli.packages import deps_block  # lazy: avoids circular import
        deps = deps_block(profile.root)
    except Exception:
        deps = ""
    if deps.strip():
        out += deps

    if notes_block:
        out += (
            "\n## ULTRON.md (project memory)\n"
            f"{notes_block}\n"
        )

    return out
