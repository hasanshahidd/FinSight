"""Hybrid retrieval: dense (Chroma) + sparse (BM25) + Reciprocal Rank Fusion."""

import json
import os
from collections import defaultdict
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


_BM25_PATH = Path(settings.chroma_persist_dir) / "bm25_corpus.json"


# ---------------------------------------------------------------------------
# BM25 corpus (persisted as JSON next to ChromaDB)
# ---------------------------------------------------------------------------

_bm25_state: dict | None = None


def _tokenize(text: str) -> list[str]:
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split() if w]


def save_bm25_corpus(ids: list[str], docs: list[str], metadatas: list[dict]) -> None:
    """Persist the BM25 corpus alongside ChromaDB. Called from ingest.py."""
    _BM25_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ids": ids,
        "docs": docs,
        "metadatas": metadatas,
        "tokenized": [_tokenize(d) for d in docs],
    }
    _BM25_PATH.write_text(json.dumps(payload), encoding="utf-8")
    global _bm25_state
    _bm25_state = None  # invalidate
    logger.info("bm25_corpus_saved", count=len(ids))


def _load_bm25() -> dict | None:
    global _bm25_state
    if _bm25_state is not None:
        return _bm25_state
    if not _BM25_PATH.exists():
        return None
    payload = json.loads(_BM25_PATH.read_text(encoding="utf-8"))
    payload["bm25"] = BM25Okapi(payload["tokenized"])
    _bm25_state = payload
    return payload


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple rankings using RRF. Returns [(id, score), ...] sorted desc."""
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# Top-level hybrid retriever
# ---------------------------------------------------------------------------


def hybrid_retrieve(
    query: str,
    chroma_collection,
    k_dense: int = 20,
    k_sparse: int = 20,
    final_k: int = 12,
) -> list[dict]:
    """Run dense + sparse retrieval, fuse with RRF, return top final_k.

    Each item: {id, text, source, chunk, dense_score, sparse_score, fused_score}.
    """
    # Dense
    dense_ids: list[str] = []
    dense_docs: dict[str, dict] = {}
    try:
        embedder = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
        [embedding] = embedder.embed_documents([query])
        res = chroma_collection.query(query_embeddings=[embedding], n_results=k_dense)
        for cid, doc, meta, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0],
            strict=False,
        ):
            dense_ids.append(cid)
            dense_docs[cid] = {
                "id": cid, "text": doc, "source": meta.get("source", "unknown"),
                "chunk": meta.get("chunk", 0),
                "dense_score": round(1 - float(dist), 4),
            }
    except Exception as exc:
        logger.warning("dense_retrieve_failed", err=str(exc))

    # Sparse (BM25)
    sparse_ids: list[str] = []
    sparse_scores: dict[str, float] = {}
    bm = _load_bm25()
    if bm is not None:
        try:
            scores = bm["bm25"].get_scores(_tokenize(query))
            ranked = sorted(
                ((cid, float(s)) for cid, s in zip(bm["ids"], scores)),
                key=lambda x: x[1], reverse=True,
            )[:k_sparse]
            for cid, s in ranked:
                sparse_ids.append(cid)
                sparse_scores[cid] = round(s, 4)
                if cid not in dense_docs:
                    idx = bm["ids"].index(cid)
                    dense_docs[cid] = {
                        "id": cid,
                        "text": bm["docs"][idx],
                        "source": bm["metadatas"][idx].get("source", "unknown"),
                        "chunk": bm["metadatas"][idx].get("chunk", 0),
                        "dense_score": 0.0,
                    }
        except Exception as exc:
            logger.warning("sparse_retrieve_failed", err=str(exc))

    fused = reciprocal_rank_fusion([dense_ids, sparse_ids])
    out: list[dict] = []
    for cid, fused_score in fused[:final_k]:
        if cid not in dense_docs:
            continue
        d = dense_docs[cid].copy()
        d["sparse_score"] = sparse_scores.get(cid, 0.0)
        d["fused_score"] = round(fused_score, 4)
        out.append(d)
    return out
