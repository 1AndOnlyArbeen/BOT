"""Codebase RAG — ingest entire repos, chunk code intelligently per language,
embed, and answer 'how do I X?' by retrieving the actual code that does X."""
from __future__ import annotations

import re
import shutil
import tempfile
import time
import zipfile
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    Language,
)

from config import DATA_DIR, EMBED_MODEL


CODEBASE_DIR = DATA_DIR / "codebase_index"
CODEBASE_DIR.mkdir(parents=True, exist_ok=True)


LANG_BY_EXT = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".c": Language.C,
    ".cpp": Language.CPP,
    ".h": Language.CPP,
    ".cs": getattr(Language, "CSHARP", Language.JAVA),
    ".swift": Language.SWIFT,
    ".kt": Language.KOTLIN,
    ".scala": Language.SCALA,
    ".html": Language.HTML,
    ".md": Language.MARKDOWN,
    ".sol": Language.SOL,
}

TEXT_EXTS = {
    ".sql", ".sh", ".yaml", ".yml", ".toml", ".json", ".xml", ".env.example",
    ".css", ".scss", ".less", ".vue", ".svelte", ".astro",
}

SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".nuxt", "target", "out", ".cache", "coverage", ".idea", ".vscode",
    ".pytest_cache", ".mypy_cache", "vendor",
}

SKIP_FILE_RE = re.compile(r"\.(lock|min\.js|min\.css|map|woff2?|ttf|otf|png|jpg|jpeg|gif|webp|ico|pdf|zip|tar|gz)$", re.I)

MAX_FILE_BYTES = 200_000


@lru_cache(maxsize=1)
def _store() -> Chroma:
    return Chroma(
        persist_directory=str(CODEBASE_DIR),
        embedding_function=OllamaEmbeddings(model=EMBED_MODEL),
        collection_name="codebase",
    )


def _splitter_for(ext: str) -> RecursiveCharacterTextSplitter:
    lang = LANG_BY_EXT.get(ext.lower())
    if lang:
        return RecursiveCharacterTextSplitter.from_language(
            language=lang, chunk_size=1000, chunk_overlap=120,
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=120,
        separators=["\n\n", "\n", " ", ""],
    )


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in LANG_BY_EXT or path.suffix.lower() in TEXT_EXTS:
        return True
    if path.name in {"Dockerfile", "Makefile", "README", "LICENSE"}:
        return True
    return False


def _walk_repo(root: Path) -> list[Path]:
    out = []
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file():
            continue
        if SKIP_FILE_RE.search(p.name):
            continue
        if not _is_text_file(p):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        out.append(p)
    return out


def _detect_symbol(chunk_text: str, ext: str) -> str:
    """Best-effort: extract function/class name from a chunk to enrich metadata."""
    if ext in (".py",):
        m = re.search(r"^\s*(?:async\s+)?def\s+(\w+)|^\s*class\s+(\w+)", chunk_text, re.M)
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        m = re.search(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
            r"^\s*(?:export\s+)?const\s+(\w+)\s*=|"
            r"^\s*class\s+(\w+)",
            chunk_text, re.M,
        )
    else:
        m = None
    if m:
        for g in m.groups():
            if g:
                return g
    return ""


def _ingest_files(repo_name: str, files: list[Path], root: Path) -> int:
    docs: list[Document] = []
    for fp in files:
        ext = fp.suffix.lower()
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not text.strip():
            continue
        rel = str(fp.relative_to(root))
        splitter = _splitter_for(ext)
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            symbol = _detect_symbol(chunk, ext)
            content = f"FILE: {rel}\nSYMBOL: {symbol or '?'}\n\n{chunk}"
            docs.append(Document(
                page_content=content,
                metadata={
                    "repo": repo_name,
                    "path": rel,
                    "ext": ext,
                    "symbol": symbol,
                    "chunk": i,
                    "ts": time.time(),
                },
            ))
    if not docs:
        return 0
    BATCH = 200
    for i in range(0, len(docs), BATCH):
        _store().add_documents(docs[i:i + BATCH])
    return len(docs)


def ingest_path(repo_name: str, root: str | Path) -> dict:
    root = Path(root).expanduser().resolve()
    if not root.exists():
        return {"error": f"{root} not found"}
    files = _walk_repo(root)
    chunks = _ingest_files(repo_name, files, root)
    return {"repo": repo_name, "files": len(files), "chunks": chunks, "root": str(root)}


def ingest_zip(repo_name: str, zip_path: str | Path) -> dict:
    z = Path(zip_path)
    if not z.exists():
        return {"error": f"{zip_path} not found"}
    tmp = Path(tempfile.mkdtemp(prefix="ultron_repo_"))
    try:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(tmp)
        roots = [p for p in tmp.iterdir() if p.is_dir()]
        root = roots[0] if len(roots) == 1 else tmp
        return ingest_path(repo_name, root)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def search_codebase(query: str, repo: str = "", k: int = 8) -> list[dict]:
    flt = {"repo": repo} if repo else None
    try:
        if flt:
            results = _store().similarity_search_with_score(query, k=k, filter=flt)
        else:
            results = _store().similarity_search_with_score(query, k=k)
    except Exception:
        return []
    out = []
    for doc, score in results:
        out.append({
            "path": doc.metadata.get("path", ""),
            "symbol": doc.metadata.get("symbol", ""),
            "repo": doc.metadata.get("repo", ""),
            "ext": doc.metadata.get("ext", ""),
            "chunk": doc.metadata.get("chunk", 0),
            "score": float(score),
            "content": doc.page_content,
        })
    return out


def list_repos() -> list[dict]:
    try:
        meta = _store().get(include=["metadatas"])
        repos: dict[str, dict] = {}
        for m in meta["metadatas"]:
            r = m.get("repo", "?")
            entry = repos.setdefault(r, {"repo": r, "chunks": 0, "files": set()})
            entry["chunks"] += 1
            entry["files"].add(m.get("path", ""))
        return [
            {"repo": r, "chunks": v["chunks"], "files": len(v["files"])}
            for r, v in repos.items()
        ]
    except Exception:
        return []


def list_repo_files(repo: str) -> list[str]:
    try:
        meta = _store().get(include=["metadatas"], where={"repo": repo})
        return sorted({m.get("path", "") for m in meta["metadatas"]})
    except Exception:
        return []


def delete_repo(repo: str) -> bool:
    try:
        _store().delete(where={"repo": repo})
        return True
    except Exception:
        return False


def reset_all() -> None:
    try:
        _store().delete_collection()
    except Exception:
        pass
    _store.cache_clear()
