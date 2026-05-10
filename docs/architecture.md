# FinSight AI - Architecture

This document expands the README's high-level diagram with rationale and request-lifecycle detail.

## Component map

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser (React + Vite, port 5173)                                       │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ App.tsx                                                          │    │
│  │  ├─ Header                                                       │    │
│  │  ├─ Sidebar  ── suggested prompts ─┐                             │    │
│  │  ├─ ChatWindow ── useChat() hook  │                             │    │
│  │  │    ├─ MessageBubble (markdown + citations)                   │    │
│  │  │    └─ ToolTrace (live agent decision visualization)          │    │
│  │  └─ InsightsPanel ── /api/insights/{summary,trend} ─┐           │    │
│  └────────────┬─────────────────────────────────────────┼───────────┘    │
└───────────────┼─────────────────────────────────────────┼────────────────┘
                ▼                                         ▼
   POST n8n webhook                            GET FastAPI /api/insights
                │                                         │
┌───────────────┼─────────────────────────────────────────┼─────────────┐
│   n8n  (port 5678)                                      │             │
│   Webhook → Validate → HTTP Request ──────► FastAPI ────┘             │
│                                              port 8000                │
│   ▼ Log Interaction → Respond ────► back to browser                   │
└───────────────────────────────────────────────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI backend  (Python 3.11+, uvicorn)                            │
│                                                                      │
│  /api/auth          mock JWT issue                                   │
│  /api/transactions  list/filter (mock banking)                       │
│  /api/insights      summary, trend                                   │
│  /api/chat          ─► LangGraph agent                               │
│                          │                                           │
│                          ▼                                           │
│   ┌──────────────────────────────────────────────────────────┐       │
│   │ LangGraph: START → llm ↔ tools → END                     │       │
│   │  llm node = ChatOpenAI(gpt-4o-mini).bind_tools(ALL_TOOLS)│       │
│   │  tools node = ToolNode([                                 │       │
│   │     get_transactions,                                    │       │
│   │     get_spending_summary,                                │       │
│   │     get_spending_trend,                                  │       │
│   │     search_financial_knowledge ])                        │       │
│   │  checkpointer = AsyncSqliteSaver (multi-turn memory)     │       │
│   └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│   ┌─────────────┐   ┌──────────────┐   ┌─────────────────────────┐   │
│   │ SQLAlchemy  │   │ insights/    │   │ rag/                    │   │
│   │ async       │   │ analyzer.py  │   │ retriever.py            │   │
│   │ + SQLite    │   │              │   │ + ChromaDB persistent   │   │
│   └─────────────┘   └──────────────┘   └─────────────────────────┘   │
│                                                                      │
│   core/cache.py (Redis)   core/logging.py (structlog JSON)           │
└──────────────────────────────────────────────────────────────────────┘
```

## Request lifecycle: a chat message

1. **User types** "How much did I spend on food last week?" in the React UI.
2. **`useChat.send()`** appends a `user` message + `pending` assistant placeholder, then `POST`s to the n8n webhook.
3. **n8n Webhook** receives the payload. The **Validate** node checks `message` is non-empty and ≤ 2000 chars.
4. **HTTP Request node** forwards to `http://host.docker.internal:8000/api/chat`.
5. **FastAPI `/api/chat`** loads (or compiles, on first call) the LangGraph and invokes it with `thread_id = "{user_id}:{session_id}"`. The SQLite checkpointer hydrates prior conversation state.
6. **`llm_node`** sends the full history + system prompt to `gpt-4o-mini` with all four tools bound. The model **decides on its own** which tools to call - this is where "no hardcoded routing" is enforced.
7. For "spent on food last week", the model emits a `get_spending_summary(period="last_7_days")` *and* `get_transactions(category="Dining", date_from=...)` tool call. **`tools_node`** executes both in parallel, attaches results as `ToolMessage`s.
8. **`llm_node` runs again** with tool outputs in context. It now produces a final natural-language answer.
9. The `/api/chat` endpoint walks the resulting `messages` list, extracts `(text, tool_calls, citations)` and returns a `ChatResponse`.
10. **n8n Log node** records the interaction (session, query, tools called).
11. **Respond node** returns JSON to the browser with permissive CORS.
12. **`useChat`** swaps the `pending` message with the real response. **`ToolTrace`** renders the agent's decision path visibly under the bubble.
13. **`InsightsPanel`** re-fetches `/api/insights/*` on `messages.length` change, so charts evolve with the conversation.

## Key design decisions

### LangGraph over LangChain agents
LangChain's `AgentExecutor` works but obscures state. LangGraph makes the graph explicit (`StateGraph(AgentState)`) and exposes the message list, tool calls, and checkpointer cleanly. The hiring rubric explicitly forbids hardcoded routing - making the routing a property of the LLM's tool-calling output (vs. our code) is structurally provable.

### n8n in the live path, not as a side-car
Many submissions wire n8n as a logging cron. We chose to put it on the request critical path because the spec says n8n should "orchestrate". Risk: an extra hop (~10–30ms) and a Docker dependency. Mitigation: `VITE_CHAT_TRANSPORT=backend` lets us bypass n8n during local debugging.

### ChromaDB embedded vs. external vector DB
Embedded ChromaDB (in-process) keeps the demo deployable as a single Python process. For scale we'd swap to Qdrant or pgvector, but for ~80 chunks the difference is undetectable.

### SQLite for the mock bank
The agent calls real HTTP endpoints for transactions (not in-memory dicts), so the integration shape matches a real-bank scenario - a Plaid swap would only require changing the underlying repo behind the routes.

### Mock JWT auth
Real auth is out of scope for an assessment. We issue a JWT so the system *demonstrates* the integration shape (`Authorization: Bearer ...`, FastAPI dependency on `current_user`) without bringing in a full IdP.

## Trade-offs and limitations

- **Single demo user.** Schema and code support multi-user, but the seed script only populates `user_1`.
- **OpenAI dependency.** Embeddings + LLM both default to OpenAI. To run fully offline, swap in Ollama for the LLM and `sentence-transformers` for embeddings (config flags exist).
- **No streaming.** The agent returns a single completed response. Streaming is a worthwhile future improvement (`graph.astream_events`).
- **In-process ChromaDB.** Persisted on disk, but not concurrent across processes. Fine for the demo.
- **Mock data is deterministic** (seeded RNG) - same numbers every reseed, which is good for demo reproducibility but unrealistic for stress testing.

## Where to extend

- Stream agent tokens to the UI (`useChat` already supports the message-update pattern).
- Add a transaction-categorization tool that lets the agent re-tag messy descriptions.
- Add a budget-comparison tool: "am I on track for my monthly food budget?" requires user-provided budget targets - currently absent.
- Wire Redis cache around `search_financial_knowledge` (queries repeat across users).
- Replace mock auth with Clerk / Auth0 / Keycloak for a real demo.
