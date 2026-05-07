"""Vector search over ingested documents."""
from rag.ingest import get_vectorstore
from config import RETRIEVE_K


def search(query: str, k: int = RETRIEVE_K) -> str:
    """Retrieve top-k chunks formatted for LLM context."""
    vs = get_vectorstore()
    try:
        results = vs.similarity_search(query, k=k)
    except Exception as e:
        return f"[rag error] {e}"

    if not results:
        return "No relevant documents found."

    parts = []
    for i, doc in enumerate(results, 1):
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        loc = f"{src}" + (f" p.{page}" if page != "" else "")
        parts.append(f"[{i}] ({loc})\n{doc.page_content.strip()}")
    return "\n\n".join(parts)


def rag_context(query: str, k: int = RETRIEVE_K, max_chars: int = 1500) -> str:
    """Format retrieved chunks for system-prompt injection.

    Returns "" when the store is empty or nothing relevant matched, so the
    block can be unconditionally concatenated into the prompt.
    """
    vs = get_vectorstore()
    try:
        results = vs.similarity_search(query, k=k)
    except Exception:
        return ""

    if not results:
        return ""

    parts = []
    for i, doc in enumerate(results, 1):
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        loc = src + (f" p.{page}" if page != "" else "")
        snippet = doc.page_content.strip()
        parts.append(f"[{i}] ({loc})\n{snippet}")

    block = "\n\n".join(parts)[:max_chars]
    return f"\n\nRELEVANT DOCUMENTS (from the user's RAG corpus — cite as [1], [2], …):\n{block}\n"
