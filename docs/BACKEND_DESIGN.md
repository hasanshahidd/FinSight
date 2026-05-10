# FinSight AI — Backend Design (v2)

> **North star:** an AI engineer reviewing this should look at the architecture and say "that's how I'd build it in production." Not just a working chatbot — a system with real agency, observability, and grounded reasoning, on a data foundation rich enough to demonstrate every claim.

This document defines the **target backend** (what we're building toward in the 3-day sprint), not the current scaffold. The scaffold from Sprint 0 will be partially rewritten — sections marked **(REPLACE)** indicate where.

---

## 0. What's wrong with "checking the boxes"

The assessment lists 6 capabilities. A naive submission ships:

- 1 LangChain agent with `if/else` masquerading as tool-calling
- 1 RAG pipeline with vanilla cosine similarity
- 1 mock API returning hand-crafted JSON
- 1 n8n workflow that's a webhook → backend pass-through
- 100 lines of seed data
- A Streamlit UI

That meets the spec. It does not differentiate. The decisions below are deliberate departures from the box-checking baseline.

---

## 1. Architecture (target)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Frontend (React)                                                            │
└──────────────┬───────────────────────────────────────────────────────────────┘
               │  POST /webhook/finance-chat   (HTTP)                          
               │  GET /api/insights/*          (HTTP, direct)                  
               │  WS  /api/chat/stream         (WebSocket, streaming tokens)   
               ▼                                                               
┌──────────────────────────────────────────────────────────────────────────────┐
│  n8n  (port 5678) — orchestration layer                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │ Webhook → Auth check → Rate-limit (Redis) → Switch by intent class   │    │
│  │   ├── chat   → HTTP → backend /api/chat                              │    │
│  │   ├── error  → Slack/log + structured 4xx                            │    │
│  │   └── audit  → append to event log → respond                         │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────┬───────────────────────────────────────────────────────────────┘
               ▼                                                               
┌──────────────────────────────────────────────────────────────────────────────┐
│  FastAPI backend (port 8000)                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Middleware: request-id · auth · structured logs · prometheus metrics  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──── Agent layer (LangGraph) ──────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │   ┌──────────────┐         routes to                                 │   │
│  │   │  SUPERVISOR  │ ─────────────────┐                                │   │
│  │   │  (router LLM)│                  ▼                                │   │
│  │   └──────────────┘    ┌─────────────────────────────────┐            │   │
│  │           ▲           │  ┌────────┐  ┌────────────┐    │            │   │
│  │           │           │  │ Txn    │  │ Knowledge  │    │            │   │
│  │           │           │  │ Analyst│  │ Advisor    │    │            │   │
│  │           │           │  └────────┘  └────────────┘    │            │   │
│  │           │           │  ┌────────┐  ┌────────────┐    │            │   │
│  │           │           │  │ Budget │  │ Anomaly    │    │            │   │
│  │           │           │  │ Coach  │  │ Detective  │    │            │   │
│  │           │           │  └────────┘  └────────────┘    │            │   │
│  │           │           └────────────────┬────────────────┘            │   │
│  │           └────── result ──────────────┘                             │   │
│  │                                                                      │   │
│  │   Memory:  AsyncSqliteSaver (per-thread checkpoints)                 │   │
│  │            + summary-buffer compaction at >40 turns                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──── Tool catalog (13 tools, cached) ─────────────────────────────────┐   │
│  │  Transactions:  get_transactions · search_transactions_semantic ·    │   │
│  │                 get_recurring_transactions · find_unusual_transactions│   │
│  │  Insights:      get_spending_summary · get_spending_trend ·          │   │
│  │                 compare_periods · forecast_spending ·                │   │
│  │                 analyze_category_drift                               │   │
│  │  Knowledge:     search_financial_knowledge (hybrid + reranker)       │   │
│  │  Budgets:       get_budgets · evaluate_budget_status · propose_budget│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│           │                    │                    │                        │
│           ▼                    ▼                    ▼                        │
│  ┌──────────────┐   ┌────────────────────┐   ┌───────────────────────┐      │
│  │ SQLite +     │   │ pandas analytics   │   │ Hybrid retriever      │      │
│  │ SQLAlchemy   │   │ - z-score anomaly  │   │ - dense (Chroma)      │      │
│  │ (txns, users,│   │ - recurring detect │   │ - sparse (BM25)       │      │
│  │  budgets,    │   │ - linear forecast  │   │ - reciprocal rank     │      │
│  │  accounts)   │   │ - period compare   │   │   fusion              │      │
│  └──────────────┘   └────────────────────┘   │ - cross-encoder       │      │
│                                              │   reranker (local)    │      │
│                                              └───────────────────────┘      │
│                                                                              │
│  Cross-cutting:  Redis (cache + rate limit) · Langfuse (tracing) ·           │
│                  Prometheus (metrics) · structlog (JSON logs)                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-agent design (the headline change)

### 2.1 Why supervisor + specialists, not one agent

A single agent with 13 tools picks fine on average but degrades on ambiguous queries ("am I doing okay?"). Specialists with focused prompts make grounded decisions. The supervisor is itself an LLM call — **routing is still a model decision, not an `if/else`**, satisfying the rubric's hardest line item.

### 2.2 Roles

| Agent | When invoked | Tools available |
|---|---|---|
| **Supervisor** | First — every turn | None directly. Outputs a `RouteDecision(specialist, rationale)` via structured output. May reroute after a specialist replies. |
| **Transaction Analyst** | Specific transactional questions ("food spend last week") | `get_transactions`, `search_transactions_semantic`, `get_recurring_transactions`, `compare_periods`, `analyze_category_drift` |
| **Knowledge Advisor** | Pure conceptual / educational queries | `search_financial_knowledge` |
| **Budget Coach** | Goal-setting, "am I on track", saving advice | `get_spending_summary`, `get_budgets`, `evaluate_budget_status`, `propose_budget`, `forecast_spending`, `search_financial_knowledge` |
| **Anomaly Detective** | "Is anything weird?", "what's draining my account?" | `find_unusual_transactions`, `get_recurring_transactions`, `get_transactions` |

### 2.3 LangGraph topology

```python
StateGraph(AgentState):
    nodes:
        supervisor          # router LLM with structured output
        transaction_analyst # ReAct subgraph
        knowledge_advisor   # ReAct subgraph
        budget_coach        # ReAct subgraph
        anomaly_detective   # ReAct subgraph
        finalizer           # collates specialist output(s) into final response

    edges:
        START → supervisor
        supervisor → conditional(route)
            "transaction_analyst" → transaction_analyst → finalizer
            "knowledge_advisor"   → knowledge_advisor   → finalizer
            "budget_coach"        → budget_coach        → finalizer
            "anomaly_detective"   → anomaly_detective   → finalizer
            "multiple"            → fan-out to N specialists in parallel → finalizer
        finalizer → END
```

Each specialist is itself a small `llm ↔ tools` ReAct loop (LangGraph's `create_react_agent`). State (messages) is shared across the supergraph; each specialist sees the prior conversation.

### 2.4 Fallback

If multi-agent shows reliability problems by mid-Day-2, we collapse to a single tool-calling agent with all 13 tools. The tool catalog and everything below this section are unchanged.

---

## 3. Tool catalog

> **Design rule:** every tool returns structured JSON the LLM can reason over, plus a `_summary` field with a one-line natural-language description it can quote directly.

### 3.1 Transaction tools

#### `get_transactions(date_from?, date_to?, category?, merchant?, account?, min_amount?, max_amount?, limit=50)`
List transactions with filters. Returns rows + aggregate (count, sum) + a `_summary`.

#### `search_transactions_semantic(query, k=20)`
Embed `query` and search a transaction-description vector index. Lets the agent answer "show me my coffee runs" or "anything that looks like a subscription" even when categories don't match exactly.
- **Index built at ingest time** over `merchant + description` per transaction.
- **Stored alongside the SQLite row id**, so the LLM gets back full transaction objects.

#### `get_recurring_transactions(min_occurrences=3, tolerance_pct=15)`
Auto-detect recurring charges. Returns an array of `{merchant, category, typical_amount, cadence_days, last_seen, count}`.
- **Algorithm:** group by `(merchant, sign)`, find sequences with consistent spacing (median ± tolerance) and consistent amounts.
- Powers prompts like "what subscriptions do I have?" and feeds the *Anomaly Detective*.

#### `find_unusual_transactions(period="last_30_days", z_threshold=2.5)`
Per-category z-score over the last 90 days. Returns transactions whose absolute amount is `z_threshold` standard deviations from the category's mean.
- Surfaces real outliers ("you usually spend $25–$60 at restaurants — this $230 charge stands out").

### 3.2 Insights tools

#### `get_spending_summary(period)`
Total spent / income / net + top categories + transaction count. (Already in scaffold; will be upgraded to use pandas.)

#### `get_spending_trend(period)`
Daily/weekly timeseries + `pct_change_vs_previous`. Pandas resample + rolling.

#### `compare_periods(period_a, period_b, by="category")`
Side-by-side breakdown of two periods. Returns rows with `(label, a_total, b_total, abs_delta, pct_delta)`.
- Handles "this week vs last week", "this month vs same month last year", arbitrary ISO ranges.

#### `forecast_spending(period="this_month", method="linear")`
Project end-of-month spend per category from current pace. `method` picks between linear extrapolation and a 4-week-rolling-mean baseline. Returns `{category, projected, actual_so_far, on_pace_for}`.

#### `analyze_category_drift(window_days=90)`
Which categories grew/shrank most over the window. Returns ranked deltas with significance flags (drift > 1 σ of prior period).

### 3.3 Knowledge tool

#### `search_financial_knowledge(query, k=4)`
Hybrid retrieval: dense (Chroma) + BM25 + cross-encoder reranking. Returns chunks with `{text, source, chunk_idx, score, rerank_score}`.
- Pipeline detailed in §5.

### 3.4 Budget tools

#### `get_budgets(user_id)`
Returns the user's budget targets `{category, monthly_limit, currency}`. Pre-seeded per persona.

#### `evaluate_budget_status(user_id, period="this_month")`
For every budget category: `{category, budget, actual, projected_eom, status: "under" | "on_track" | "warning" | "over"}`.

#### `propose_budget(months_lookback=3, savings_rate=0.20)`
Suggests a budget based on the user's actual spend pattern, targeting a savings rate. Returns the same shape as `get_budgets` so the user can compare.

### 3.5 Tool execution rules

- **All tools cached** in Redis, key = `(tool_name, sorted-args-hash, user_id)`, TTL = 5 min.
- **All tools traced** via Langfuse — duration, args (PII-redacted), result size.
- **All tools enforce `user_id` scope** at the SQL layer; agents cannot read across users.
- **All tools return `{"_summary": ...}`** for the LLM to quote directly without re-derivation.

---

## 4. Data model & seed strategy

### 4.1 The honest answer to "is the current data enough?"

**No.** The current seed has:
- ~250 transactions
- 90 days
- 1 user
- 1 account (implicit)
- No budgets
- No baked-in stories (anomalies, recurring drift)

That's enough to demo "list my transactions". It is not enough to demo:
- *Anomaly detection* — needs real outliers to find
- *Recurring detection* — needs ≥3 occurrences per pattern, so ≥6 months for monthly subs
- *Forecasting* — needs trend
- *Period comparisons* — needs ≥2 comparable periods
- *"My spending changed because…"* — needs categories that actually shifted

### 4.2 Target dataset

| Dimension | Current | Target |
|---|---|---|
| Time range | 90 days | **240 days** (~8 months) |
| Total transactions | ~250 | **~2,400** |
| Users | 1 | **5 personas** (see §4.4) |
| Accounts per user | 1 | **3** (checking, savings, credit card) |
| Categories | 10 | **14** with **sub-categories** for Dining, Shopping, Transit |
| Distinct merchants | ~20 | **80+** |
| Budgets | 0 | **per-user category targets** |
| Baked-in stories | 0 | **8** (see §4.5) |

### 4.3 Schema upgrade **(REPLACE)**

```python
class User:           id, email, name, persona, created_at
class Account:        id, user_id, type ("checking"|"savings"|"credit"), balance_cents
class Transaction:    id, user_id, account_id, amount, currency, category, subcategory,
                      merchant, description, timestamp, is_recurring, anomaly_score
class Budget:         id, user_id, category, monthly_limit_cents, currency
class RecurringRule:  id, user_id, merchant, typical_amount_cents, cadence_days,
                      next_expected_at, confidence
class Conversation:   id, user_id, session_id, started_at, last_at, message_count
class TraceEvent:     id, request_id, agent, tool, args_hash, duration_ms, ts
```

`Transaction.is_recurring` and `anomaly_score` are pre-computed at seed time — gives the agent fast lookups without recomputing on every query, while the *tools* still re-derive on demand for "live" queries.

### 4.4 Personas (the 5 demo users)

Each persona is a deliberate scenario the agent can reason about. Demos can switch personas to show range.

| Persona | Profile | Story |
|---|---|---|
| **Alex** (`user_1`) | NYC SWE, 28, single | Default demo. High rent, dining-heavy, recent gym subscription added. |
| **Sam** (`user_2`) | Family of 4, suburban | Groceries dominate. Two kids' activities. One big medical bill in month 3. |
| **Jordan** (`user_3`) | Grad student | Variable income (assistantship + freelance gigs). Tight budget. Subscription creep. |
| **Riley** (`user_4`) | High-earning consultant | Travel-heavy. Investment transfers monthly. Dining out 4–5x/week. |
| **Casey** (`user_5`) | Recovering debt | Multiple credit cards, paying down. No savings yet. Visible avalanche pattern. |

### 4.5 Baked-in stories (so the agent has something to find)

| Story | User | What the agent should detect |
|---|---|---|
| **Subscription creep** | Alex | 3 new monthly subs added gradually (gym, streaming, AI tool). Total recurring up 41% over 6 months. |
| **Surprise medical bill** | Sam | $1,820 charge in month 3, far above category median (z > 4). |
| **Vacation week** | Riley | 7 consecutive days of travel + dining + entertainment, ~$2,400 total. Anomalous *cluster*. |
| **Income raise** | Alex | Payroll deposits step up by 14% at month 5. |
| **Annual insurance** | Sam | Single $1,250 annual auto-insurance hit in month 2. |
| **Gradual dining drift** | Alex | Dining moves from $350/mo to $560/mo over 4 months. Should surface in `analyze_category_drift`. |
| **Overdraft event** | Casey | One day with negative checking balance — visible in account history. |
| **Tax refund** | Jordan | $1,400 deposit in March. Income spike. |

### 4.6 Generation approach

A single `scripts/generate_demo_data.py` driver writes deterministic data (seeded RNG). Personas are encoded as Python objects with knobs for category weights, merchant pools, monthly budgets, and **story injectors** that splice in the events above at the right dates.

---

## 5. RAG pipeline (hybrid + reranker)

### 5.1 Why upgrade from vanilla cosine

Pure dense retrieval misses queries that hinge on rare terms (specific framework names, dollar amounts, acronyms). Pure BM25 misses semantic paraphrases. Combining + reranking is a 5–15 percentage point precision gain on most QA benchmarks and is genuinely impressive in a demo.

### 5.2 Pipeline

```
query
  │
  ├─► (optional) HyDE rewrite — generate a hypothetical answer, embed that
  │
  ├─► dense retrieval     (Chroma cosine, k=20)  ──┐
  │                                                ├─► RRF fusion ──► top 12
  ├─► sparse retrieval    (BM25 over chunks, k=20)─┘
  │
  └─► cross-encoder rerank (ms-marco-MiniLM, local) ──► top 4
                                                              │
                                                              ▼
                                                       agent context
```

- **Dense:** ChromaDB, `text-embedding-3-small`. Persistent on disk.
- **Sparse:** `rank_bm25` in-process; rebuilt at ingest time, fits in RAM (small corpus).
- **Fusion:** Reciprocal Rank Fusion (RRF, k=60) — parameterless and robust.
- **Reranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2` from sentence-transformers. ~80MB, runs on CPU, ~50ms for 12 pairs.
- **HyDE:** off by default (extra LLM call); on for queries where dense+sparse top result has score below threshold.

### 5.3 Knowledge base expansion

The 13 docs from Sprint 0 are **kept** but augmented to ~20 docs total. Add:
- Net worth tracking
- Tax-advantaged accounts (401k vs IRA vs HSA)
- Home buying readiness
- Healthcare costs / FSA-HSA rules
- Insurance basics
- Lifestyle creep
- Mortgage refinancing
- Financial independence (FIRE) basics

Each doc 400–800 words. ~20 docs × ~6 chunks/doc = ~120 chunks.

### 5.4 Citation grounding

After the agent drafts its answer, a small post-processor marks each numeric/factual claim that came from a retrieved chunk with `[source.md:chunk_idx]`. The frontend renders these as hover-preview pills. Anchors the answer visibly in the corpus.

---

## 6. Memory & long-context

- **Per-thread checkpointer** (AsyncSqliteSaver) keyed by `(user_id, session_id)`.
- **Summary buffer compaction:** when message count > 40 *or* token estimate > 12k, a summarizer LLM call rewrites the oldest 30 messages into a single `SystemMessage("Earlier in this conversation: …")`.
- **Cross-session "pinned facts":** structured per-user notes (e.g., "user prefers metric units", "user is debt-averse") inserted as a system message every turn — small, opt-in, manually curated for demo.

---

## 7. Streaming

Use FastAPI + `WebSocket` for `/api/chat/stream`. Stream events:

```
event: token        — assistant token delta
event: tool_call    — { name, args } when supervisor selects
event: tool_result  — { name, summary } when tool returns
event: route        — { specialist, rationale } when supervisor routes
event: done         — { tool_calls, citations, message }
```

Frontend's `ToolTrace` component renders these live so the user *sees* the agent thinking.

REST `/api/chat` remains for non-streaming integrations (n8n).

---

## 8. Observability

### 8.1 Tracing — Langfuse (self-hosted via docker-compose)

Every request gets a trace with nested spans:

```
trace: chat
  span: supervisor.invoke         (model, tokens_in, tokens_out, $)
  span: route → budget_coach
  span: budget_coach.invoke
    span: tool: get_spending_summary  (cache=hit/miss, ms, rows)
    span: tool: get_budgets
    span: tool: evaluate_budget_status
    span: tool: search_financial_knowledge
      span: dense_retrieve
      span: sparse_retrieve
      span: rerank
  span: finalizer
```

Trace IDs propagate via `X-Request-Id` header through n8n into the backend.

### 8.2 Metrics — Prometheus + `prometheus-fastapi-instrumentator`

- `chat_requests_total{status}`
- `chat_duration_seconds_bucket`
- `tool_invocation_total{tool_name, status}`
- `tool_duration_seconds_bucket{tool_name}`
- `llm_tokens_total{model, kind=in|out}`
- `llm_cost_usd_total{model}`
- `cache_events_total{kind=hit|miss|set}`
- `rag_score_bucket{stage=dense|sparse|rerank}`

Scraped at `/metrics`.

### 8.3 Logs — structlog JSON

Every log line carries `request_id`, `user_id`, `session_id`. Pretty-rendered locally (`LOG_FORMAT=console`), JSON in production. PII (email, raw amounts above $1000) redacted at the formatter level.

### 8.4 Cost tracking

`langchain_openai` exposes `usage_metadata`. Per-trace cost is computed (`token_count × per-model rate`) and stored. Surfaced on a `/api/admin/cost` endpoint and in Langfuse.

---

## 9. Caching, rate limiting, security

### 9.1 Caching layers

| Layer | Key | TTL | Why |
|---|---|---|---|
| Tool result cache | `(tool, hash(args), user_id)` | 5 min | Most tool calls within a session are repeated as agents iterate |
| Embedding cache | `hash(text)` | 24 hr | RAG queries repeat across users |
| Knowledge retrieval cache | `(query, k)` | 1 hr | Knowledge corpus is static |
| LLM response cache | `hash(messages)` | off in prod, on for tests | Determinism in eval runs |

### 9.2 Rate limiting (n8n + Redis)

Token-bucket per `(user_id, minute)` enforced in n8n's pre-flight. 30 messages/min default, 200/hour. Returns `429` with `Retry-After`.

### 9.3 Auth

Mock JWT (`user_id` in `sub`) for the demo. Production-ready hooks: `get_current_user` is a FastAPI dep that swaps to a real IdP by changing one import.

### 9.4 Tool sandboxing

`ToolNode` wraps every tool with `(timeout=15s, exception_handler=err→llm)`. A failing tool returns a structured error to the LLM rather than crashing the graph — the LLM is instructed to retry with corrected args once before falling back.

---

## 10. Evaluation framework

### 10.1 Golden set

`tests/eval/golden.jsonl` — 40+ queries, each with:

```json
{"query": "How much did I spend on food last week?",
 "expected_route": "transaction_analyst",
 "expected_tools_subset": ["get_spending_summary"],
 "must_contain_facts": ["dollar_amount_for_dining"],
 "must_not_contain": ["I cannot access your transactions"]}
```

### 10.2 Runner

`pytest tests/eval/test_agent.py` runs the golden set against the live agent (with `LLM_RESPONSE_CACHE=on` for determinism) and asserts:

- Route matches expected (when specified).
- Tool sequence is a superset of `expected_tools_subset`.
- Final answer contains required facts (validated by an LLM-as-judge call with a strict rubric).
- No forbidden phrases.

Scores reported as `{routing_accuracy, tool_coverage, factual_grounding, safety}` — a 4-axis vector you can show in the demo.

---

## 11. API surface (final)

```
GET  /health
GET  /metrics                            — Prometheus

POST /api/auth/login                      — mock JWT
GET  /api/auth/me

GET  /api/users                           — list personas (for the demo persona switcher)
GET  /api/accounts                        — user's accounts

GET  /api/transactions                    — filtered list
GET  /api/transactions/{id}
GET  /api/transactions/recurring          — auto-detected
GET  /api/transactions/anomalies          — outliers
POST /api/transactions/search             — semantic search

GET  /api/insights/summary?period=…
GET  /api/insights/trend?period=…
GET  /api/insights/compare?a=…&b=…
GET  /api/insights/forecast?period=…
GET  /api/insights/category-drift?window=…

GET  /api/budgets
PUT  /api/budgets/{category}              — update target
POST /api/budgets/propose                 — generate proposal

POST /api/chat                            — REST, single-shot
WS   /api/chat/stream                     — streaming events
GET  /api/chat/history?session_id=…

GET  /api/admin/cost                      — token + $ rollup
GET  /api/admin/eval                      — last eval run results
```

---

## 12. What gets thrown away from Sprint 0

| Sprint 0 file | Action | Reason |
|---|---|---|
| `app/db/seed.py` | **REPLACE** | Single-user, story-less |
| `app/agent/graph.py` | **REPLACE** | Single agent, no supervisor |
| `app/agent/tools.py` | **EXTEND** | 4 tools → 13 |
| `app/insights/analyzer.py` | **REWRITE** as `app/analytics/` | Move to pandas, add forecast/anomaly/compare |
| `app/rag/retriever.py` | **EXTEND** | Add BM25 + RRF + reranker |
| `app/api/chat.py` | **EXTEND** | Add WS streaming endpoint |
| `app/main.py` | **EXTEND** | Add Prometheus, Langfuse, request-id middleware |
| `n8n/workflows/finance-assistant.json` | **EXTEND** | Add rate-limit + auth-check + audit branch |
| Everything else | Keep as-is | Schemas, config, scaffolding |

---

## 13. Open questions (need user input)

1. **OpenAI key budget** — Langfuse self-host, hybrid RAG, and 5-persona seeds will burn ~5–10k tokens of embeddings + ~50–150 chat-test calls. Are we OK with ~$2–5 of OpenAI spend during dev?
2. **Self-hosting Langfuse vs LangSmith** — Langfuse runs locally in Docker (free, more setup); LangSmith is hosted (free tier, less setup). Recommend Langfuse for the "no external dependency" story but it adds 2 containers. OK?
3. **Cross-encoder reranker** — adds ~80MB of model weights and ~50ms per RAG call. Worth it for the demo polish? (I think yes.)
4. **Multi-agent vs single agent** — committing to multi-agent makes Day 2 tighter. Want me to keep multi-agent as the headline goal, or play it safe with a single agent + 13 tools?
5. **Streaming WebSocket** — adds frontend complexity. Skip and keep REST? (Recommend keeping — visible win in demo.)

Defaults if you don't answer: yes / Langfuse / yes / multi-agent with single-agent fallback / keep streaming.
