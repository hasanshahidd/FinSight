"""Chat REST endpoint — invokes the multi-agent supergraph."""

import json
import time
from typing import Any

from fastapi import APIRouter
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.citations import extract_citations
from app.agent.graph import get_graph
from app.config import settings
from app.core.cost import estimate_cost, record_session_cost
from app.core.logging import get_logger
from app.core.metrics import CHAT_DURATION_SECONDS, CHAT_REQUESTS_TOTAL
from app.core.tracing import trace_config
from app.db.personas import get_persona
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallTrace

router = APIRouter()
logger = get_logger(__name__)


def _preview(content: Any, limit: int = 320) -> str:
    """Build a human-readable preview of a tool's result.

    Tools return `{ "_summary": "<one-line>", ...rest }`. Surface that summary
    so the UI shows clean text, not truncated JSON.
    """
    if content is None:
        return ""
    parsed: Any = content
    if isinstance(content, str):
        s = content.strip()
        if s.startswith("{"):
            try:
                parsed = json.loads(s)
            except Exception:
                return s[:limit]
        else:
            return s[:limit]
    if isinstance(parsed, dict):
        summary = parsed.get("_summary")
        if isinstance(summary, str) and summary.strip():
            return summary[:limit]
        # Fallback: join readable top-level keys
        keys = [k for k in parsed.keys() if k != "_summary"][:4]
        bits = []
        for k in keys:
            v = parsed[k]
            if isinstance(v, list):
                bits.append(f"{k}: {len(v)} item(s)")
            elif isinstance(v, dict):
                bits.append(f"{k}: …")
            else:
                bits.append(f"{k}: {str(v)[:40]}")
        return " · ".join(bits)[:limit]
    try:
        return json.dumps(parsed, default=str)[:limit]
    except Exception:
        return str(parsed)[:limit]


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    persona = get_persona(req.user_id)
    persona_desc = persona.description if persona else ""

    graph = get_graph()
    config: dict = {"configurable": {"thread_id": f"{req.user_id}:{req.session_id}"}}
    config.update(trace_config(session_id=req.session_id, user_id=req.user_id))

    started = time.time()
    state = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=req.message)],
            "user_id": req.user_id,
            "persona_desc": persona_desc,
            "route": None,
            "rationale": None,
        },
        config=config,
    )

    # Collect tool-call traces and final assistant text
    tool_calls: list[ToolCallTrace] = []
    final_text = ""
    pending_call_by_id: dict[str, ToolCallTrace] = {}

    for msg in state["messages"]:
        if isinstance(msg, AIMessage):
            if msg.content:
                # Multiple AI messages may exist (specialist iterations);
                # the final non-empty one is the answer.
                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                if text.strip():
                    final_text = text
            for tc in msg.tool_calls or []:
                trace = ToolCallTrace(
                    name=tc["name"],
                    args=tc.get("args", {}) or {},
                    result_preview="",
                )
                tool_calls.append(trace)
                if tc.get("id"):
                    pending_call_by_id[tc["id"]] = trace
        elif isinstance(msg, ToolMessage):
            preview = _preview(msg.content)
            if msg.tool_call_id and msg.tool_call_id in pending_call_by_id:
                pending_call_by_id[msg.tool_call_id].result_preview = preview
            else:
                # fall back: attach to the last unfilled trace with matching name
                for trace in reversed(tool_calls):
                    if trace.name == msg.name and not trace.result_preview:
                        trace.result_preview = preview
                        break

    citations = extract_citations(state["messages"])
    structured = {
        "route": state.get("route"),
        "rationale": state.get("rationale"),
    }

    duration_s = time.time() - started
    duration_ms = int(duration_s * 1000)

    # Cost tracking
    cost = estimate_cost(state["messages"], settings.llm_model)
    await record_session_cost(req.session_id, cost)

    # Metrics
    route = state.get("route") or "unknown"
    CHAT_REQUESTS_TOTAL.labels(transport="rest", route=route, status="ok").inc()
    CHAT_DURATION_SECONDS.labels(route=route).observe(duration_s)

    logger.info(
        "chat_done",
        session=req.session_id,
        user=req.user_id,
        route=state.get("route"),
        tools=len(tool_calls),
        citations=len(citations),
        ms=duration_ms,
        tokens=cost["total_tokens"],
        cost_usd=cost["estimated_cost_usd"],
    )

    return ChatResponse(
        message=final_text,
        session_id=req.session_id,
        tool_calls=tool_calls,
        citations=citations,
        structured_data=structured,
    )
