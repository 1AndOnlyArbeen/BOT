"""Document ingestion: load, chunk, embed, persist.

Accepts: PDF, DOCX, MD, TXT via langchain loaders, plus *any* file that
decodes as UTF-8/latin-1 text (code, JSON, YAML, CSV, logs, …). Also
exposes ingest_text() so callers can paste raw text of any size — the
splitter handles arbitrary length.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from config import (
    CHROMA_DIR,
    DOCS_DIR,
    EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

LOADERS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".docx": Docx2txtLoader,
}


def _read_as_text(path: Path) -> str | None:
    for enc in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, OSError):
            continue
    return None


def _load_one(path: Path) -> list[Document]:
    loader_cls = LOADERS.get(path.suffix.lower())
    if loader_cls is not None:
        try:
            return loader_cls(str(path)).load()
        except Exception as e:
            print(f"[ingest] loader failed for {path.name} ({e}); falling back to text")

    text = _read_as_text(path)
    if text is None:
        print(f"[ingest] skip {path.name}: not decodable as text")
        return []
    return [Document(page_content=text, metadata={"source": path.name})]


def _split(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def get_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="docs",
    )


def ingest_files(paths: Iterable[Path]) -> int:
    """Ingest given files into the vector store. Returns chunk count."""
    docs: list[Document] = []
    for p in paths:
        loaded = _load_one(p)
        for d in loaded:
            d.metadata["source"] = p.name
        docs.extend(loaded)

    if not docs:
        return 0

    chunks = _split(docs)
    vs = get_vectorstore()
    vs.add_documents(chunks)
    return len(chunks)


def ingest_text(text: str, source: str = "pasted") -> int:
    """Ingest raw text (any size) under a given source label."""
    text = (text or "").strip()
    if not text:
        return 0
    doc = Document(page_content=text, metadata={"source": source})
    chunks = _split([doc])
    vs = get_vectorstore()
    vs.add_documents(chunks)
    return len(chunks)


def ingest_uploaded(uploaded_files) -> int:
    """Save Streamlit uploads to disk then ingest."""
    saved = []
    for f in uploaded_files:
        dest = DOCS_DIR / f.name
        dest.write_bytes(f.getbuffer())
        saved.append(dest)
    return ingest_files(saved)


def list_sources() -> list[str]:
    """Return distinct source labels currently in the vector store."""
    vs = get_vectorstore()
    try:
        meta = vs.get(include=["metadatas"])
        sources = {m.get("source", "?") for m in meta["metadatas"]}
        return sorted(sources)
    except Exception:
        return []


def delete_source(source: str) -> int:
    """Remove all chunks belonging to a given source label. Returns deleted count."""
    vs = get_vectorstore()
    try:
        existing = vs.get(where={"source": source}, include=["metadatas"])
        ids = existing.get("ids") or []
        if not ids:
            return 0
        vs.delete(ids=ids)
        return len(ids)
    except Exception as e:
        print(f"[ingest] delete_source failed: {e}")
        return 0


def reset_vectorstore() -> None:
    """Wipe the vector store entirely."""
    vs = get_vectorstore()
    try:
        vs.delete_collection()
    except Exception:
        pass
