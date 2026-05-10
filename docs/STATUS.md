# Project Status

A snapshot of what's built, what's not, and what each sprint covered.

## Sprint 0 — Scaffold ✅

84 files. Project structure, Vite/React frontend skeleton with full design system, FastAPI app boot, ChromaDB plumbing, 13 RAG docs, n8n workflow stub, basic seed (90 days, 1 user). Foundation for everything below.

## Sprint 1 — "The bank is real" ✅

Theme: data + analytics layer is production-grade before any LLM touches it.

- ✅ Schema upgrade: `User`, `Account`, `Transaction` (+ subcategory, is_recurring, anomaly_score), `Budget`, `RecurringRule`
- ✅ 5 personas with category weights, merchant pools, subscriptions, budgets, story injectors
- ✅ Deterministic data generator: 240 days × 5 personas × ~2,400 transactions × 8 baked-in stories
- ✅ pandas analytics layer: 7 modules (summary, trend, compare, forecast, drift, anomaly, recurring)
- ✅ Transaction semantic-search index built lazily per user
- ✅ API endpoints: `/api/users{,/me,/{id}/accounts}`, `/api/transactions/{,/recurring,/anomalies,/search,/categories}`, `/api/insights/{summary,trend,compare,forecast,category-drift}`, `/api/budgets/{,/status,/propose}`
- ✅ Request-id middleware + structlog JSON logging
- ✅ Smoke tests for analytics + API

## Sprint 2 — "The agent is real" ✅

Theme: multi-agent supervisor + hybrid RAG + streaming.

- ✅ 13-tool catalog (transactions, insights, knowledge, budgets)
- ✅ Supervisor with `ChatOpenAI.with_structured_output(RouteDecision)` — model-decided routing
- ✅ 4 specialist ReAct subgraphs with focused tool subsets and dedicated markdown prompts
- ✅ LangGraph supergraph: `START → supervisor → conditional → specialist → END`
- ✅ Memory compaction (summary-buffer at >40 messages)
- ✅ Hybrid retrieval: dense (Chroma) + sparse (BM25) + RRF fusion
- ✅ Cross-encoder reranker (optional; lazy-loaded; graceful fallback)
- ✅ Citation extraction from ToolMessage chain
- ✅ WebSocket streaming with `route / tool_call / tool_result / done / error` events
- ✅ Frontend `useChatStream` hook with live event handling
- ✅ +8 new knowledge docs (21 total)

## Audit pass ✅

Eight findings from the pre-Sprint-3 audit fixed:

1. ✅ Deleted orphaned `app/insights/` directory
2. ✅ Deleted conflicting `app/agent/prompts.py` file (clashed with the `prompts/` package)
3. ✅ Added missing fields to `TransactionOut` schema (`subcategory`, `is_recurring`, `anomaly_score`, `account_id`)
4. ✅ Removed risky `@cached_tool` decorator stack (caching moved out of tool path)
5. ✅ Unified `useChat` hook auto-routes to streaming/REST based on transport
6. ✅ Added `pytest.ini` with `asyncio_mode = auto`
7. ✅ Strongly-typed `TransactionSearchRequest` body model
8. ✅ Frontend `.env.example` simplified — drops confusing transport flag

## Sprint 3 — "The system is real" ✅

Theme: observability, n8n hardening, eval, demo polish.

- ✅ Langfuse self-hosted via docker-compose (+ Postgres)
- ✅ `app/core/tracing.py` — Langfuse callback handler wiring; injected into chat invocations
- ✅ `app/core/metrics.py` — custom Prometheus counters/histograms (chat requests, tool invocations, tokens, cost, RAG latency, cache events)
- ✅ `app/core/cost.py` — token + USD cost tracking per session and globally; aggregated in Redis
- ✅ `/api/admin/cost` and `/api/admin/eval` endpoints
- ✅ `n8n/workflows/finance-assistant.json` v2: validate → auth check → rate limit → backend → audit log → respond, with branching for errors
- ✅ Eval harness: 30 golden queries in `tests/eval/golden.jsonl`, LLM-as-judge in `judge.py`, runner in `runner.py`, pytest wrapper that asserts loose floors

## Sprint 4 — "The system is shipped" ✅

Theme: frontend integration, demo wiring, README polish.

- ✅ Updated `lib/types.ts` with User, Account, Citation, EvalScoreboard, CostRollup
- ✅ Updated `lib/api.ts` with fetchUsers, fetchMe, fetchCost, fetchEvalScores
- ✅ `useChatStream` accepts `user_id` per call
- ✅ `usePersona` hook with localStorage persistence
- ✅ `PersonaSwitcher` component (top-right in Header)
- ✅ `RouteIndicator` component (above each AI message; color-coded by specialist)
- ✅ `CitationPill` with hover-preview of source chunk
- ✅ `EvalScoreboard` component in the right panel
- ✅ MessageBubble integrates RouteIndicator + CitationPill + ToolTrace
- ✅ Header includes PersonaSwitcher; switch resets the chat thread
- ✅ Updated `App.tsx` to wire persona context end-to-end; insights re-fetch on persona change
- ✅ Polished `README.md` with full setup, architecture, examples
- ✅ `docs/demo-script.md` — 7-minute recording walkthrough

## What's left

- ⏳ **Demo video recording** — user-led; can't be automated. Script in [docs/demo-script.md](demo-script.md).
- ⏳ **End-to-end smoke test** — user-led; run the stack and verify each capability described in the demo script. Bug-fix as needed.
- ⏳ **Optional polish from runtime** — anything caught during smoke testing.

## Sprints remaining

**Zero implementation sprints remaining.** What's left is the user-led demo recording and any runtime fixes from smoke testing — typically 0–1 short polish passes after that.

Definition-of-done from the original sprint plan, status:

- [x] One command (`docker compose up -d`) brings up the entire backplane
- [x] Two commands bring up the app (uvicorn + npm run dev)
- [x] 5 personas exist with realistic 240-day data and embedded stories
- [x] 13 tools callable from the agent; all return structured JSON
- [x] Multi-agent supervisor routes via LLM (no hardcoded `if/else`)
- [x] Hybrid RAG retrieves with reranking; citations rendered in UI
- [x] WebSocket streaming shows live tool-call events
- [x] n8n workflow enforces auth + rate limit + audit log
- [x] Langfuse captures every chat trace with nested spans
- [x] `pytest tests/eval` produces a 4-axis score
- [x] README, architecture doc, setup doc, example queries, demo script all current
- [ ] Demo video recorded and linked from README

Final task: record the demo video.

## File counts

| Area | Count |
|---|---|
| Backend Python | ~75 |
| Frontend TypeScript/TSX | ~24 |
| Knowledge docs (RAG corpus) | 21 |
| Eval golden queries | 30 |
| Documentation pages | 7 |
| **Total project files** | **~145** |
