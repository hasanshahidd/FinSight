"""Extract citations from a ToolMessage chain.

When `search_financial_knowledge` is called during an agent run, its result
contains chunks with `source` + `chunk` + `rerank_score`. We surface these to
the UI as structured citation objects.
"""

import json
from typing import Any

from langchain_core.messages import ToolMessage


def extract_citations(messages: list) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, ToolMessage):
            continue
        if m.name != "search_financial_knowledge":
            continue
        try:
            payload = m.content if isinstance(m.content, dict) else json.loads(m.content)
        except Exception:
            continue
        for c in payload.get("chunks") or []:
            out.append({
                "source": c.get("source"),
                "chunk": c.get("chunk"),
                "score": c.get("rerank_score") or c.get("fused_score") or c.get("dense_score"),
                "preview": (c.get("text") or "")[:240],
            })
    # Deduplicate by (source, chunk)
    seen = set()
    deduped = []
    for c in out:
        key = (c["source"], c.get("chunk"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped
