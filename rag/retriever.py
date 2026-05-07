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
