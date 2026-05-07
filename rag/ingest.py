"""Document ingestion: load, chunk, embed, persist."""
from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
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


def _load_one(path: Path):
    loader_cls = LOADERS.get(path.suffix.lower())
    if not loader_cls:
        return []
    try:
        return loader_cls(str(path)).load()
    except Exception as e:
        print(f"[ingest] failed {path.name}: {e}")
        return []


def _split(docs):
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
    docs = []
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


def ingest_uploaded(uploaded_files) -> int:
    """Save Streamlit uploads to disk then ingest."""
    saved = []
    for f in uploaded_files:
        dest = DOCS_DIR / f.name
        dest.write_bytes(f.getbuffer())
        saved.append(dest)
    return ingest_files(saved)


def list_sources() -> list[str]:
    """Return distinct source filenames currently in the vector store."""
    vs = get_vectorstore()
    try:
        meta = vs.get(include=["metadatas"])
        sources = {m.get("source", "?") for m in meta["metadatas"]}
        return sorted(sources)
    except Exception:
        return []


def reset_vectorstore() -> None:
    """Wipe the vector store entirely."""
    vs = get_vectorstore()
    try:
        vs.delete_collection()
    except Exception:
        pass
