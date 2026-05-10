"""WebSocket streaming chat endpoint.

Emits structured events as the multi-agent graph runs:
  { "type": "route",       "specialist": ..., "rationale": ... }
  { "type": "tool_call",   "name": ..., "args": {...} }
  { "type": "tool_result", "name": ..., "summary": ... }
  { "type": "done",        "message": ..., "tool_calls": [...], "citations": [...] }
  { "type": "error",       "message": ... }
"""

import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.citations import extract_citations
from app.agent.graph import get_graph
from app.core.logging import get_logger
from app.db.personas import get_persona

router = APIRouter()
logger = get_logger(__name__)


def _safe_json(obj: Any) -> Any:
    """Best-effort JSON-serializable conversion."""
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return str(obj)


def _summary_of_tool_output(out: Any) -> str:
    if out is None:
        return ""
    if isinstance(out, ToolMessage):
        out = out.content
    if isinstance(out, str):
        try:
            parsed = json.loads(out)
            return parsed.get("_summary", "") if isinstance(parsed, dict) else out[:200]
        except Exception:
            return out[:200]
    if isinstance(out, dict):
        return out.get("_summary", "") or json.dumps(out, default=str)[:200]
    return str(out)[:200]


@router.websocket("/api/chat/stream")
async def chat_stream(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
            except Exception as exc:
                await ws.send_json({"type": "error", "message": f"bad json: {exc}"})
                continue

            message = (payload.get("message") or "").strip()
            session_id = payload.get("session_id", "default")
            user_id = payload.get("user_id", "user_1")
            if not message:
                await ws.send_json({"type": "error", "message": "message is required"})
                continue

            persona = get_persona(user_id)
            persona_desc = persona.description if persona else ""

            graph = get_graph()
            config = {"configurable": {"thread_id": f"{user_id}:{session_id}"}}
            graph_input = {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "persona_desc": persona_desc,
                "route": None,
                "rationale": None,
            }

            started = time.time()
            try:
                async for event in graph.astream_events(graph_input, config=config, version="v2"):
                    et = event.get("event")
                    name = event.get("name", "")
                    data = event.get("data", {}) or {}

                    if et == "on_chain_end" and name == "supervisor":
                        out = data.get("output") or {}
                        if isinstance(out, dict) and out.get("route"):
                            await ws.send_json({
                                "type": "route",
                                "specialist": out.get("route"),
                                "rationale": out.get("rationale", ""),
                            })
                    elif et == "on_tool_start":
                        await ws.send_json({
                            "type": "tool_call",
                            "name": name,
                            "args": _safe_json(data.get("input", {})),
                        })
                    elif et == "on_tool_end":
                        await ws.send_json({
                            "type": "tool_result",
                            "name": name,
                            "summary": _summary_of_tool_output(data.get("output")),
                        })
            except Exception as exc:
                logger.error("stream_invoke_failed", err=str(exc))
                await ws.send_json({"type": "error", "message": str(exc)})
                continue

            # Pull final state for the answer + citations + traces
            snapshot = await graph.aget_state(config)
            messages = snapshot.values.get("messages", []) if snapshot else []

            tool_calls: list[dict] = []
            final_text = ""
            pending_by_id: dict[str, dict] = {}
            for m in messages:
                if isinstance(m, AIMessage):
                    if m.content:
                        text = m.content if isinstance(m.content, str) else str(m.content)
                        if text.strip():
                            final_text = text
                    for tc in m.tool_calls or []:
                        trace = {
                            "name": tc["name"],
                            "args": _safe_json(tc.get("args", {}) or {}),
                            "result_preview": "",
                        }
                        tool_calls.append(trace)
                        if tc.get("id"):
                            pending_by_id[tc["id"]] = trace
                elif isinstance(m, ToolMessage):
                    preview = m.content if isinstance(m.content, str) else json.dumps(m.content, default=str)
                    preview = (preview or "")[:320]
                    if m.tool_call_id and m.tool_call_id in pending_by_id:
                        pending_by_id[m.tool_call_id]["result_preview"] = preview

            citations = extract_citations(messages)

            await ws.send_json({
                "type": "done",
                "message": final_text,
                "tool_calls": tool_calls,
                "citations": citations,
                "session_id": session_id,
                "duration_ms": int((time.time() - started) * 1000),
                "route": snapshot.values.get("route") if snapshot else None,
                "rationale": snapshot.values.get("rationale") if snapshot else None,
            })

    except WebSocketDisconnect:
        logger.info("ws_disconnect")
    except Exception as exc:
        logger.error("ws_error", err=str(exc))
        try:
            await ws.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
