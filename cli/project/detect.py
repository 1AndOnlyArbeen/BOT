"""Project profile detection.

Reads the well-known marker files at the workspace root and produces a
typed `ProjectProfile`. Pure inspection — no LLM calls — so it's cheap to
run on every turn (we still cache per workspace path).

The profile feeds into the system prompt so the model knows, at minimum:
- what languages and frameworks are in play,
- which package manager / test runner / build command to prefer,
- whether the workspace is a git repo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from config import WORKSPACE_DIR


# --- Profile dataclass -----------------------------------------------------

@dataclass(frozen=True)
class ProjectProfile:
    root: Path
    name: str
    languages: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    package_manager: str | None = None
    test_command: str | None = None
    build_command: str | None = None
    run_command: str | None = None
    detected_files: tuple[str, ...] = ()
    is_git: bool = False
    is_empty: bool = False

    def summary(self) -> str:
        bits: list[str] = []
        if self.languages:
            bits.append("/".join(self.languages))
        if self.frameworks:
            bits.append("+".join(self.frameworks))
        if self.package_manager:
            bits.append(self.package_manager)
        return " · ".join(bits) or "unknown stack"


# --- Marker readers --------------------------------------------------------
#
# Each helper returns (languages, frameworks, package_manager, commands_dict).
# Keep them small and forgiving — a malformed manifest must not crash detection.

_FRAMEWORK_HINTS_JS = {
    "react": ("react",),
    "next": ("next.js",),
    "vue": ("vue",),
    "svelte": ("svelte",),
    "express": ("express",),
    "fastify": ("fastify",),
    "nestjs": ("nestjs",),
    "vite": ("vite",),
    "tailwindcss": ("tailwind",),
}


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _from_package_json(root: Path) -> dict:
    pkg = _read_json(root / "package.json")
    if not isinstance(pkg, dict):
        return {}

    deps = {}
    for key in ("dependencies", "devDependencies"):
        d = pkg.get(key)
        if isinstance(d, dict):
            deps.update(d)

    is_ts = (root / "tsconfig.json").exists() or "typescript" in deps
    languages = ("typescript", "javascript") if is_ts else ("javascript",)

    frameworks: list[str] = []
    for marker, fws in _FRAMEWORK_HINTS_JS.items():
        if any(marker in name for name in deps):
            frameworks.extend(fws)

    pm = "npm"
    if (root / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (root / "yarn.lock").exists():
        pm = "yarn"
    elif (root / "bun.lockb").exists():
        pm = "bun"

    scripts = pkg.get("scripts") or {}
    test_cmd = None
    if "test" in scripts:
        test_cmd = f"{pm} test"
    build_cmd = None
    if "build" in scripts:
        build_cmd = f"{pm} run build"
    run_cmd = None
    for k in ("dev", "start"):
        if k in scripts:
            run_cmd = f"{pm} run {k}"
            break

    return {
        "languages": languages,
        "frameworks": tuple(frameworks),
        "package_manager": pm,
        "test_command": test_cmd,
        "build_command": build_cmd,
        "run_command": run_cmd,
        "name": pkg.get("name") or root.name,
    }


def _from_pyproject(root: Path) -> dict:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}

    text = ""
    try:
        text = pyproject.read_text(encoding="utf-8")
    except Exception:
        return {}

    frameworks: list[str] = []
    low = text.lower()
    for marker, label in (
        ("fastapi", "fastapi"),
        ("flask", "flask"),
        ("django", "django"),
        ("starlette", "starlette"),
        ("langchain", "langchain"),
        ("pydantic", "pydantic"),
        ("streamlit", "streamlit"),
    ):
        if marker in low and label not in frameworks:
            frameworks.append(label)

    pm = "uv" if (root / "uv.lock").exists() else (
        "poetry" if "[tool.poetry]" in text else "pip"
    )

    test_cmd = None
    if "pytest" in low:
        test_cmd = "pytest" if pm == "pip" else f"{pm} run pytest"

    name = root.name
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("name") and "=" in s:
            try:
                name = s.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
            break

    return {
        "languages": ("python",),
        "frameworks": tuple(frameworks),
        "package_manager": pm,
        "test_command": test_cmd,
        "build_command": None,
        "run_command": None,
        "name": name,
    }


def _from_requirements(root: Path) -> dict:
    req = root / "requirements.txt"
    if not req.exists():
        return {}

    text = ""
    try:
        text = req.read_text(encoding="utf-8").lower()
    except Exception:
        return {}

    frameworks: list[str] = []
    for marker in ("fastapi", "flask", "django", "starlette", "langchain", "streamlit"):
        if marker in text:
            frameworks.append(marker)

    return {
        "languages": ("python",),
        "frameworks": tuple(frameworks),
        "package_manager": "pip",
        "test_command": "pytest" if "pytest" in text else None,
        "build_command": None,
        "run_command": None,
        "name": root.name,
    }


def _from_cargo(root: Path) -> dict:
    cargo = root / "Cargo.toml"
    if not cargo.exists():
        return {}
    return {
        "languages": ("rust",),
        "frameworks": (),
        "package_manager": "cargo",
        "test_command": "cargo test",
        "build_command": "cargo build",
        "run_command": "cargo run",
        "name": root.name,
    }


def _from_gomod(root: Path) -> dict:
    gomod = root / "go.mod"
    if not gomod.exists():
        return {}
    return {
        "languages": ("go",),
        "frameworks": (),
        "package_manager": "go",
        "test_command": "go test ./...",
        "build_command": "go build ./...",
        "run_command": "go run .",
        "name": root.name,
    }


# --- Combine ---------------------------------------------------------------

_DETECTORS = (_from_package_json, _from_pyproject, _from_requirements, _from_cargo, _from_gomod)


def _pick_first_truthy(profiles: list[dict], key: str):
    for p in profiles:
        v = p.get(key)
        if v:
            return v
    return None


def detect_project(root: Path | None = None) -> ProjectProfile:
    """Inspect the workspace root and return a ProjectProfile.

    Multiple manifests are merged: a polyglot repo (Python backend + JS
    frontend) gets BOTH languages, with the JS package manager taking
    priority for run/build commands when present.
    """
    root = (root or WORKSPACE_DIR).resolve()
    profiles = [d(root) for d in _DETECTORS]
    profiles = [p for p in profiles if p]

    detected_files: list[str] = []
    for marker in (
        "package.json", "pyproject.toml", "requirements.txt",
        "Cargo.toml", "go.mod", "tsconfig.json", "Dockerfile",
        "docker-compose.yml", "Makefile", "README.md", "CLAUDE.md",
    ):
        if (root / marker).exists():
            detected_files.append(marker)

    is_git = (root / ".git").exists()
    is_empty = not any(root.iterdir()) if root.exists() else True

    languages: tuple[str, ...] = tuple(dict.fromkeys(
        lang for p in profiles for lang in p.get("languages", ())
    ))
    frameworks: tuple[str, ...] = tuple(dict.fromkeys(
        fw for p in profiles for fw in p.get("frameworks", ())
    ))

    name = next((p["name"] for p in profiles if p.get("name")), root.name)
    package_manager = _pick_first_truthy(profiles, "package_manager")
    test_command = _pick_first_truthy(profiles, "test_command")
    build_command = _pick_first_truthy(profiles, "build_command")
    run_command = _pick_first_truthy(profiles, "run_command")

    return ProjectProfile(
        root=root,
        name=name,
        languages=languages,
        frameworks=frameworks,
        package_manager=package_manager,
        test_command=test_command,
        build_command=build_command,
        run_command=run_command,
        detected_files=tuple(detected_files),
        is_git=is_git,
        is_empty=is_empty,
    )


@lru_cache(maxsize=8)
def _cached(root_str: str) -> ProjectProfile:
    return detect_project(Path(root_str))


def project_profile(root: Path | None = None) -> ProjectProfile:
    """Cached entry point — call this everywhere instead of detect_project()."""
    root = (root or WORKSPACE_DIR).resolve()
    return _cached(str(root))


def invalidate(root: Path | None = None) -> None:
    """Drop the cached profile for a workspace (call after major changes)."""
    if root is None:
        _cached.cache_clear()
    else:
        try:
            _cached.cache_clear()
        except Exception:
            pass
