# FinSight AI — Sprint Plan

> Three days. Backend-led. Five gates: a working backend, a real dataset, a multi-agent graph, a hybrid RAG, and a recorded demo. Each day ends with a demo-able artifact.

This plan operationalizes [BACKEND_DESIGN.md](./BACKEND_DESIGN.md). If anything in this plan contradicts the design doc, the design doc wins.

---

## 0. Goals & scoring criteria

The hiring rubric (from the assessment + my read of what differentiates submissions):

| Capability | What "good" looks like | Owner sprint |
|---|---|---|
| Multi-turn chat | Memory across ≥10 turns; references prior context unprompted | S2 |
| Mock banking API | Filterable, realistic, multi-account, multi-user | S1 |
| Insights | Beyond totals: anomalies, forecasts, drift, period comparison | S1 |
| RAG | Hybrid retrieval, citations rendered in UI | S2 |
| n8n orchestration | On the live path with real logic (auth, rate-limit, audit) | S3 |
| Agent reasoning | LLM-decided routing; specialist agents; visible trace | S2 |
| **Bonuses** | Auth, caching, observability, eval, streaming, beautiful UI | S1–S3 |

**Demo gate:** at end of each sprint, I should be able to record a 30-second clip showing the new capability working.

---

## 1. Sprint 0 — Scaffold (DONE)

✅ Repo layout, FastAPI boot, React app, Tailwind design system, ChromaDB plumbing, 13 RAG docs, n8n workflow stub, basic seed (90d, 1 user). 84 files.

This is the floor. Everything below builds on it.

---

## 2. Sprint 1 — "The bank is real" (Day 1)

**Theme:** the data and analytics layer is production-grade before any LLM touches it.

### 2.1 Goals
- 5 personas × 240 days × 3 accounts × ~2,400 transactions, with **8 baked-in stories** the agent can detect.
- pandas-based analytics module with forecasting, anomaly z-scores, period comparison, category drift, recurring detection.
- Budget schema + per-persona targets seeded.
- Transaction semantic search index built at seed time.
- API surface for transactions/insights/budgets fully exposed.

### 2.2 Tasks

| # | Task | File(s) | AC |
|---|---|---|---|
| 1.1 | **Schema upgrade** — Account, Budget, RecurringRule, persona on User; sub-categories on Transaction | `app/db/models.py` | `init_db` creates all tables; existing transactions migrate or get re-seeded |
| 1.2 | **Persona definitions** — Python dataclasses per persona with category weights, merchant pools, recurring patterns, story injectors | `app/db/personas.py` (NEW) | 5 personas defined, each with ≥30 unique merchants in their pool |
| 1.3 | **Data generator** — deterministic RNG, 240 days, all 8 stories injected at correct dates | `scripts/generate_demo_data.py` (REPLACE seed_db.py) | After run: ~2,400 txns, all stories present, budgets seeded, recurring rules pre-detected |
| 1.4 | **Transaction semantic index** — embed `merchant + description` for every txn, store in a separate Chroma collection | `app/rag/transaction_index.py` (NEW) | Querying "coffee" returns Starbucks/Blue Bottle/etc rows even when category=Dining |
| 1.5 | **Analytics module** — pandas `summary`, `trend`, `compare_periods`, `forecast`, `category_drift`, `find_anomalies`, `detect_recurring` | `app/analytics/` (NEW; replaces `app/insights/`) | Each function has a unit test against a known synthetic frame |
| 1.6 | **API: transactions** — `recurring`, `anomalies`, `search` endpoints | `app/api/transactions.py` | All return 200 with valid JSON for `user_1`; auth-scoped |
| 1.7 | **API: insights** — `compare`, `forecast`, `category-drift` endpoints | `app/api/insights.py` | Same |
| 1.8 | **API: budgets** — get/put/propose | `app/api/budgets.py` (NEW) | Same |
| 1.9 | **API: users/accounts** — for the persona switcher | `app/api/users.py` (NEW) | Same |
| 1.10 | **CORS + middleware** — request-id, structured logs, CORS for n8n | `app/main.py`, `app/core/middleware.py` (NEW) | All requests carry `X-Request-Id`; logs include it |
| 1.11 | **Smoke tests** — `tests/test_api_smoke.py` covering every endpoint | `tests/` | `pytest -k smoke` green |

### 2.3 Deliverables (end of Day 1)
- `python scripts/generate_demo_data.py` produces all 5 personas + stories.
- All `/api/*` endpoints respond correctly (verified via Swagger UI walk-through).
- Recording: 30-second screen capture hitting `/api/transactions/anomalies` → real outlier appears, then `/api/insights/forecast?period=this_month` → projected EOM spend with category breakdown.

### 2.4 Risk register
- **Pandas perf** — 2,400 rows is trivial; not a real risk.
- **Story injection bugs** — stories must hit specific dates; build a `assert_stories_present()` smoke check.
- **Data fixtures duplication** — using deterministic seed (RNG seed = persona id) avoids drift.

---

## 3. Sprint 2 — "The agent is real" (Day 2)

**Theme:** multi-agent supervisor + hybrid RAG + streaming. The intellectual core.

### 3.1 Goals
- Supervisor + 4 specialist agents wired in LangGraph.
- Hybrid RAG (dense + BM25 + cross-encoder rerank) replacing vanilla cosine.
- WebSocket streaming chat with live tool-call events.
- Tool catalog at 13 tools, all cached + traced.
- Conversation memory with summary-buffer compaction.

### 3.2 Tasks

| # | Task | File(s) | AC |
|---|---|---|---|
| 2.1 | **Tool catalog v2** — 9 new tools (semantic search, recurring, anomalies, compare, forecast, drift, budgets×3) | `app/agent/tools.py` | All 13 tools callable from a Python REPL; each returns `_summary` field |
| 2.2 | **Tool-result cache** wrapper — Redis-backed | `app/agent/cache.py` (NEW) | Same args = cache hit; cache miss recomputes |
| 2.3 | **Hybrid retriever** — Chroma + BM25 + RRF fusion | `app/rag/hybrid.py` (NEW) | On test queries, hybrid > dense-only on a 5-query mini-benchmark |
| 2.4 | **Cross-encoder reranker** — `cross-encoder/ms-marco-MiniLM-L-6-v2` | `app/rag/rerank.py` (NEW) | Reranker boosts top-1 hit rate vs RRF on the mini-benchmark |
| 2.5 | **Supervisor agent** — structured-output router | `app/agent/supervisor.py` (NEW) | Given test queries, supervisor picks the correct specialist 90%+ of the time |
| 2.6 | **Specialist subgraphs** — TransactionAnalyst, KnowledgeAdvisor, BudgetCoach, AnomalyDetective | `app/agent/specialists/` (NEW) | Each specialist runs a ReAct loop with its tool subset |
| 2.7 | **Supergraph composition** — wire supervisor → specialist → finalizer | `app/agent/graph.py` (REPLACE) | End-to-end queries route correctly; messages flow through |
| 2.8 | **Memory compaction** — summary buffer at >40 turns | `app/agent/memory.py` (NEW) | Long-conversation test: turn 50 still produces coherent answer in <12k tokens |
| 2.9 | **WebSocket streaming** — `/api/chat/stream` with token/tool/route/done events | `app/api/chat_stream.py` (NEW) | curl-style WS test prints incremental events in real time |
| 2.10 | **Frontend streaming** — `useChatStream` hook + ToolTrace renders live | `frontend/src/hooks/useChatStream.ts` (NEW), `ToolTrace.tsx` | Demo shows tool calls appearing one by one as agent thinks |
| 2.11 | **Citation grounding** — post-hoc tag claims with `[source.md:idx]` | `app/agent/citations.py` (NEW) | RAG answers carry visible citation pills in UI |
| 2.12 | **Prompt library** — versioned prompt files for supervisor + each specialist | `app/agent/prompts/` (REPLACE prompts.py) | Each prompt in its own `.md` file with frontmatter |

### 3.3 Deliverables (end of Day 2)
- "How much did I spend on food last week, and how does that compare to my budget?" routes to BudgetCoach, calls 3 tools, returns grounded answer in ~5s.
- "Anything weird in my recent spending?" routes to AnomalyDetective, surfaces the medical bill / vacation cluster.
- Live tool-trace appears in UI as agent thinks.
- Recording: 30s clip showing supervisor routing + tool stream + citation pill on a knowledge query.

### 3.4 Risk register
- **Multi-agent reliability** — if supervisor mis-routes >20% by mid-day, collapse to single tool-calling agent (fallback documented in design §2.4). The 13 tools and prompts are unchanged.
- **Reranker model download** — 80MB; pre-download in setup script.
- **Streaming on Windows** — uvicorn + WebSocket on Windows can be flaky; have REST fallback wired (`VITE_CHAT_TRANSPORT=backend-rest`).
- **Token cost** — supervisor + specialist is 2x calls per turn; cache aggressively, use `gpt-4o-mini`.

---

## 4. Sprint 3 — "The system is real" (Day 3)

**Theme:** observability, n8n orchestration, evaluation, and demo polish.

### 4.1 Goals
- n8n workflow with auth, rate-limit, audit, and error branches.
- Langfuse self-hosted, capturing every chat trace.
- Prometheus metrics endpoint live, basic Grafana dashboard JSON committed.
- Eval harness with 40+ golden queries, scoreboard rendering.
- Demo video recorded.

### 4.2 Tasks

| # | Task | File(s) | AC |
|---|---|---|---|
| 3.1 | **Langfuse Docker compose** — add to root compose | `docker-compose.yml` | `docker compose up` brings up n8n + redis + langfuse + postgres-for-langfuse |
| 3.2 | **Langfuse SDK wiring** — wrap LangGraph + tools | `app/core/tracing.py` (NEW) | Every chat creates a trace with nested tool spans visible in Langfuse UI |
| 3.3 | **Prometheus metrics** — instrumentator + custom counters | `app/main.py`, `app/core/metrics.py` (NEW) | `/metrics` exposes counters listed in design §8.2 |
| 3.4 | **Cost tracking** — per-model rate table; sum per request | `app/core/cost.py` (NEW) | `/api/admin/cost` returns total $ and breakdown |
| 3.5 | **n8n workflow v2** — webhook → JWT verify → Redis rate-limit → Switch (chat/audit/error) → backend → Log → respond | `n8n/workflows/finance-assistant.json` (REPLACE) | Importing into a fresh n8n instance and posting an unauthed request returns 401; authed → 200; over rate-limit → 429 |
| 3.6 | **Eval harness** — runner + LLM-as-judge | `tests/eval/test_agent.py`, `tests/eval/golden.jsonl` (NEW) | `pytest tests/eval` runs ≥40 queries, prints 4-axis score |
| 3.7 | **Eval scoreboard endpoint** — last results JSON | `app/api/admin.py` (NEW) | `/api/admin/eval` returns most recent run's scoreboard |
| 3.8 | **PII redaction** — log filter strips emails + amounts >$1k | `app/core/logging.py` | Manual test: log a redactable field → not present in JSON output |
| 3.9 | **Persona switcher** in UI — dropdown to switch demo user | `frontend/src/components/PersonaSwitcher.tsx` (NEW) | Selecting "Sam" updates insights panel; chat thread isolates per user |
| 3.10 | **Eval scoreboard UI** — small panel showing 4 scores | `frontend/src/components/EvalScores.tsx` (NEW) | Renders on `/admin` route or in Header; pulls `/api/admin/eval` |
| 3.11 | **Final README pass** — architecture diagrams, setup, demo links | `README.md`, `docs/architecture.md` | Reads cleanly to a recruiter who's never seen the project |
| 3.12 | **Demo video** — 5–10 min walkthrough | `docs/demo.md` (link to video) | Covers: chat, transactions query, insights, RAG, agent decision, n8n executions panel, Langfuse trace |

### 4.3 Deliverables (end of Day 3)
- `docker compose up -d` brings up the entire backplane.
- Langfuse at http://localhost:3000 shows live traces with nested spans.
- n8n workflow rejects unauthed and rate-limited requests.
- `pytest tests/eval` produces a published score.
- Demo video recorded and linked.

### 4.4 Risk register
- **Langfuse setup friction** — first-time install can be sticky. Have a Make target `make langfuse-up` and a documented fallback to LangSmith hosted (1-line env change).
- **Demo video re-records** — 5–10 minutes feels long; rehearse 3x with a script (committed in `docs/demo-script.md`).

---

## 5. Daily ceremony

**Start of day** (15 min):
1. Read prior day's "what stuck" notes.
2. Pull latest, run `pytest`, run smoke checks.
3. Pick the day's first task; commit a TODO list.

**Mid-day check** (10 min):
1. Are we on track for the demo gate? If not, what gets cut?
2. Any new risks? Update risk register.

**End of day** (15 min):
1. Record the 30-sec demo clip for what shipped.
2. Commit + push.
3. Write "what stuck" notes for tomorrow.

---

## 6. What gets cut if behind schedule

In priority order (cut from the bottom first):

1. ✂️ Eval scoreboard UI panel (eval still runs, just no UI)
2. ✂️ HyDE query rewrite (hybrid RAG without HyDE is still strong)
3. ✂️ Persona switcher in UI (data exists, just no toggle)
4. ✂️ Cross-encoder reranker (RRF alone is still better than vanilla cosine)
5. ✂️ Streaming WebSocket → fall back to non-streaming REST (lose visible "thinking" but core works)
6. ✂️ Multi-agent → fall back to single tool-calling agent (lose specialist routing, all 13 tools still work)

What does **not** get cut, ever:
- 5 personas × 240 days × stories
- Hybrid retrieval (at minimum dense + BM25)
- All 13 tools
- n8n on the live path with real logic
- Langfuse traces

---

## 7. Stretch goals (if ahead of schedule)

In rough priority:

1. **Code-execution tool** — sandboxed pandas tool letting the agent answer arbitrary aggregations not covered by canned tools.
2. **Conversation forking** — "what if I had asked X instead?" UI.
3. **Proactive insights** — backend cron computes daily anomalies and pushes to UI on load.
4. **Voice input** — Web Speech API + auto-submit. Cheap demo wow.
5. **Multi-currency** — at the schema level + a converter tool.
6. **Receipt OCR** — drop a receipt PNG into chat, agent extracts and adds a transaction. (Out of scope — listed for completeness.)

---

## 8. Demo script (target — 7 minutes)

1. **0:00 — Open** the app at localhost:5173. Point out: chat, prompt sidebar, live insights.
2. **0:30 — Persona switcher** demo: switch from Alex → Sam, insights re-populate.
3. **1:00 — Multi-turn transaction query**: "How much did I spend on dining last week?" → "Is that more than usual?" → "What's been driving the increase?". Show ToolTrace expanding live.
4. **2:30 — Knowledge query**: "What's the 50/30/20 rule?" Show citation pills. Hover one to preview the source chunk.
5. **3:30 — Mixed query**: "Based on my spending, suggest a budget." Show supervisor → BudgetCoach routing in trace, multiple tool calls, grounded answer.
6. **4:30 — Anomaly demo**: "Is there anything weird in my recent spending?" Should surface the medical bill / vacation cluster.
7. **5:00 — n8n** — open localhost:5678, point at the active workflow, show executions panel for the chat we just had.
8. **5:30 — Langfuse** — open localhost:3000, click into a recent trace, show nested supervisor → specialist → tool spans with token counts.
9. **6:00 — Eval** — `pytest tests/eval -q` runs in terminal, prints 4-axis score.
10. **6:30 — Wrap** — "this is the architecture" (point at diagram), key decisions (multi-agent, hybrid RAG, n8n in live path), trade-offs, what I'd do with another week.

---

## 9. Definition of done

The project is "done" when:

- [ ] One command (`docker compose up -d`) brings up the entire backplane.
- [ ] Two commands (`uvicorn ...`, `npm run dev`) bring up the app.
- [ ] Five personas exist, each with realistic 240-day data and embedded stories.
- [ ] At least 13 tools are callable from the agent; all return structured JSON.
- [ ] Multi-agent supervisor routes correctly on 90%+ of golden queries.
- [ ] Hybrid RAG retrieves with reranking; citations are rendered in UI.
- [ ] WebSocket streaming shows live tool-call events.
- [ ] n8n workflow enforces auth + rate limit + audit log.
- [ ] Langfuse captures every chat trace with nested spans.
- [ ] `pytest tests/eval` produces a 4-axis score ≥ 0.8 on each axis.
- [ ] README, architecture doc, setup doc, example queries doc all current.
- [ ] Demo video recorded and linked from README.

If a row is unchecked, it goes into a follow-up issue, not into the demo.
