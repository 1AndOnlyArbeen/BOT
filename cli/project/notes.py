"""ULTRON.md — durable per-project memory.

Lives at the workspace root next to the code. Hand-editable, git-friendly,
auto-created the first time the coder runs in a workspace. The system
prompt picks it up every turn so the model never forgets project
conventions, build commands, or whatever the user wants pinned.
"""
from __future__ import annotations

from pathlib import Path

from cli.project.detect import ProjectProfile

NOTES_FILENAME = "ULTRON.md"
MAX_NOTES_CHARS = 4000


def notes_path(profile: ProjectProfile) -> Path:
    return profile.root / NOTES_FILENAME


def _default_template(profile: ProjectProfile) -> str:
    detected = ", ".join(profile.detected_files) or "(none)"
    langs = ", ".join(profile.languages) or "unknown"
    fws = ", ".join(profile.frameworks) or "(none)"
    return (
        f"# Ultron project notes\n\n"
        f"_Auto-created on first run — edit freely. Ultron reads this every turn._\n\n"
        f"## Profile (auto-detected)\n"
        f"- **Project**: `{profile.name}`\n"
        f"- **Languages**: {langs}\n"
        f"- **Frameworks**: {fws}\n"
        f"- **Package manager**: `{profile.package_manager or 'n/a'}`\n"
        f"- **Test command**: `{profile.test_command or 'not detected'}`\n"
        f"- **Build command**: `{profile.build_command or 'not detected'}`\n"
        f"- **Run command**: `{profile.run_command or 'not detected'}`\n"
        f"- **Git repo**: {'yes' if profile.is_git else 'no'}\n"
        f"- **Detected manifests**: {detected}\n\n"
        f"## Conventions\n"
        f"_Add anything Ultron should always remember about how to write code in this repo._\n"
        f"- (e.g. 4-space indent, single quotes, snake_case for functions)\n\n"
        f"## Common commands\n"
        f"_Useful one-liners — Ultron will prefer these over guessing._\n"
        f"- (e.g. `npm run dev`, `pytest -k unit`)\n\n"
        f"## Current focus\n"
        f"_What you're working on right now — Ultron will keep this in mind._\n"
        f"- (e.g. \"rewriting the auth flow to use JWT\")\n\n"
        f"## Pinned\n"
        f"_Anything important that doesn't fit elsewhere._\n"
    )


def ensure_notes(profile: ProjectProfile) -> Path:
    """Create ULTRON.md from a template if it doesn't exist. Returns the path."""
    path = notes_path(profile)
    if not path.exists():
        try:
            path.write_text(_default_template(profile), encoding="utf-8")
        except Exception:
            # Workspace might be read-only — that's fine, just don't crash.
            pass
    return path


def read_notes(profile: ProjectProfile) -> str:
    """Read ULTRON.md if present (creating it first). Capped at MAX_NOTES_CHARS."""
    path = ensure_notes(profile)
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    if len(text) > MAX_NOTES_CHARS:
        text = text[:MAX_NOTES_CHARS] + f"\n\n…(truncated; full notes in {NOTES_FILENAME})"
    return text


def append_section(profile: ProjectProfile, heading: str, body: str) -> str:
    """Append `## heading\\n{body}\\n` to ULTRON.md. Returns the updated text."""
    path = ensure_notes(profile)
    try:
        existing = path.read_text(encoding="utf-8")
    except Exception:
        existing = ""

    block = f"\n## {heading.strip()}\n{body.strip()}\n"
    new_text = existing.rstrip() + "\n" + block
    try:
        path.write_text(new_text, encoding="utf-8")
    except Exception:
        return existing
    return new_text
