"""Top-level retriever: hybrid + optional reranker."""

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.rag.hybrid import hybrid_retrieve
from app.rag.rerank import rerank


def _client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_chroma_collection(reset: bool = False):
    client = _client()
    if reset:
        try:
            client.delete_collection(settings.chroma_collection)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str, k: int = 4, use_reranker: bool = True) -> list[dict]:
    """End-to-end retrieve with hybrid search + (optional) cross-encoder rerank."""
    collection = get_chroma_collection()
    fused = hybrid_retrieve(query, collection, k_dense=20, k_sparse=20, final_k=12)
    if not fused:
        return []
    if use_reranker:
        return rerank(query, fused, top_k=k)
    return fused[:k]
