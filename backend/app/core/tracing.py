"""Langfuse tracing wiring.

Returns a callback handler that LangChain/LangGraph will invoke for every
LLM call, tool call, and chain step. Falls back to a no-op if Langfuse env
vars aren't configured."""

import os
from functools import lru_cache

from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def langfuse_handler():
    """Return a Langfuse CallbackHandler, or None if not configured."""
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse.callback import CallbackHandler  # type: ignore
        handler = CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )
        logger.info("langfuse_enabled", host=os.getenv("LANGFUSE_HOST"))
        return handler
    except Exception as exc:
        logger.warning("langfuse_unavailable", err=str(exc))
        return None


def trace_config(session_id: str | None = None, user_id: str | None = None) -> dict:
    """Build a LangGraph/LangChain `config` dict that includes the Langfuse
    handler if available. Use as: graph.ainvoke(input, config=trace_config(...))."""
    handler = langfuse_handler()
    cfg: dict = {}
    if handler:
        cfg["callbacks"] = [handler]
        cfg["metadata"] = {
            **(cfg.get("metadata") or {}),
            "session_id": session_id,
            "user_id": user_id,
            "service": "finsight-ai",
        }
    return cfg
