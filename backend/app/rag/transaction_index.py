"""Semantic search over the user's transactions.

Embeds `merchant + description + category` per transaction into a separate
Chroma collection. Built lazily on first query for a user, refreshed when
the collection is empty or stale.
"""

from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.db.models import Transaction

logger = get_logger(__name__)


_TXN_COLLECTION_PREFIX = "txn_index_"


def _client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _collection_for(user_id: str):
    name = f"{_TXN_COLLECTION_PREFIX}{user_id}"
    return _client().get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"},
    )


def _embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)


async def _build_index_if_empty(session: AsyncSession, user_id: str) -> int:
    coll = _collection_for(user_id)
    if coll.count() > 0:
        return 0

    rows = (
        await session.execute(
            select(Transaction).where(Transaction.user_id == user_id)
        )
    ).scalars().all()
    if not rows:
        return 0

    docs = [
        f"{r.merchant} | {r.category} | {r.subcategory} | {r.description}"
        for r in rows
    ]
    ids = [r.id for r in rows]
    metas = [
        {
            "merchant": r.merchant,
            "category": r.category,
            "subcategory": r.subcategory,
            "amount": float(r.amount),
            "timestamp": r.timestamp.isoformat(),
        }
        for r in rows
    ]
    embedder = _embedder()
    embeddings = embedder.embed_documents(docs)
    coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
    logger.info("txn_index_built", user=user_id, count=len(ids))
    return len(ids)


async def semantic_search_transactions(
    session: AsyncSession,
    user_id: str,
    query: str,
    k: int = 20,
) -> dict:
    await _build_index_if_empty(session, user_id)
    coll = _collection_for(user_id)
    if coll.count() == 0:
        return {"_summary": "No transactions to search.", "matches": []}

    [embedding] = _embedder().embed_documents([query])
    res = coll.query(query_embeddings=[embedding], n_results=k)

    matches = []
    for tid, doc, meta, dist in zip(
        res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0],
        strict=False,
    ):
        matches.append({
            "id": tid,
            "merchant": meta.get("merchant"),
            "category": meta.get("category"),
            "subcategory": meta.get("subcategory"),
            "amount": meta.get("amount"),
            "timestamp": meta.get("timestamp"),
            "score": round(1 - float(dist), 4),
        })

    total = sum(abs(m["amount"]) for m in matches if m.get("amount"))
    return {
        "_summary": (
            f"Top {len(matches)} transactions matching '{query}' "
            f"(combined ${total:,.2f})"
        ),
        "query": query,
        "k": k,
        "matches": matches,
    }
