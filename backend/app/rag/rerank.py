"""Cross-encoder reranker - optional. Lazy import; degrades gracefully if
sentence-transformers is not installed."""

from app.core.logging import get_logger

logger = get_logger(__name__)

_model = None
_unavailable = False


def _load_model():
    global _model, _unavailable
    if _model is not None or _unavailable:
        return _model
    try:
        from sentence_transformers import CrossEncoder  # type: ignore
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        logger.info("cross_encoder_loaded")
    except Exception as exc:
        logger.warning("cross_encoder_unavailable", err=str(exc))
        _unavailable = True
    return _model


def rerank(query: str, candidates: list[dict], top_k: int = 4) -> list[dict]:
    """Rerank candidates by cross-encoder score. Each candidate must have
    `text`. Adds `rerank_score` to each returned item."""
    if not candidates:
        return []
    model = _load_model()
    if model is None:
        # Fallback: pass-through, sort by fused_score if present
        candidates = sorted(candidates, key=lambda c: c.get("fused_score", 0), reverse=True)
        for c in candidates:
            c["rerank_score"] = c.get("fused_score", 0)
        return candidates[:top_k]

    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    for c, s in zip(candidates, scores, strict=False):
        c["rerank_score"] = round(float(s), 4)
    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates[:top_k]
