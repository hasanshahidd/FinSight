# FinSight AI — Personal Finance Assistant

> Conversational AI assistant for personal finance. Multi-agent LangGraph supervisor + 4 specialists, hybrid RAG (dense + BM25), n8n as the only chat path (validate → rate-limit → backend → audit), and a clean React UI. Built for the AI Engineer assessment.

## ▶️ One-command start

```bash
# 1. Set your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env
# 2. Bring up the entire stack (backend + frontend + n8n + redis)
docker compose up -d
# 3. Open http://localhost:5173 — the React app is wired through n8n by default
```

After ~2 minutes (build + seed + ingest), open:
- **App** → http://localhost:5173
- **n8n Executions** → http://localhost:5678 (every chat appears live)
- **Backend API** → http://localhost:8000/docs
- **Optional Langfuse traces** → `docker compose --profile observability up -d` then http://localhost:3000

## 🗄️ How the databases are created on first run

Both **SQLite** (mock bank) and **ChromaDB** (knowledge index) are created **automatically** the first time the backend starts — no manual seeding step. The Docker entrypoint runs three commands in sequence:

```dockerfile
# backend/Dockerfile
CMD python scripts/generate_demo_data.py \
 && python scripts/ingest_docs.py \
 && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| Step | What it creates | Where it lands |
|------|-----------------|----------------|
| 1. `generate_demo_data.py` | Calls `init_db()` to create the SQLAlchemy tables, then `seed_all()` to insert **5 personas × 240 days × ~2,400 deterministic transactions** with 8 baked-in stories | `backend/data/finsight.db` (SQLite) |
| 2. `ingest_docs.py` | Reads 21 markdown docs from `data/knowledge/`, embeds them via OpenAI, and persists both the dense Chroma collection and the BM25 corpus | `backend/chroma_db/` (vector store) |
| 3. `uvicorn` | FastAPI starts; the `lifespan` hook re-runs `init_db()` (idempotent — only creates tables if missing) | API on port 8000 |

**Both seed steps are idempotent.** `seed_persona()` deletes existing rows for each user before inserting, and `get_chroma_collection(reset=True)` drops the collection before re-ingesting. So whether it's the first run or the hundredth, the resulting state is identical — reproducibility on every `docker compose up`.

The Docker volumes (`backend_data`, `backend_chroma`) persist between restarts, so subsequent boots are fast (~5 s) but still get a clean re-seed if you want.

### Local (no Docker) — run the seeds once manually

If you skip Docker and run uvicorn directly, seed the database + index once before starting the server:

```bash
cd backend
.\.venv\Scripts\Activate.ps1            # PowerShell on Windows
pip install -r requirements.txt

python scripts/generate_demo_data.py    # creates finsight.db + 5 personas
python scripts/ingest_docs.py           # creates chroma_db/ + 21 docs

uvicorn app.main:app --reload --port 8000
```

The FastAPI startup hook still calls `init_db()` automatically, so the **table schema** auto-creates on first uvicorn boot — but without step 1 the database is empty and chat queries against user data return nothing. Both `finsight.db` and `chroma_db/` are listed in `.gitignore` because they're rebuilt from the seed scripts, not committed.

## ☁️ Free-tier deployment

A complete guide to hosting the full stack for $0 — Oracle Cloud (forever-free VPS), Render, Fly.io, Hugging Face Spaces, or Cloud Run for the backend; Vercel / Cloudflare Pages / Netlify for the frontend; Upstash for managed Redis.

→ **[docs/deploy.md](docs/deploy.md)** has step-by-step recipes and a "best free combo" recommendation.

## 📊 Eval scoreboard (30 golden queries, automated)

```
routing_accuracy        0.900   27/30 — agent picked right specialist
tool_coverage           0.933   28/30 — expected tool fired
factual_heuristic       1.000   30/30 — required facts in response
safety_heuristic        1.000   30/30 — no forbidden phrases
judge_safety            1.000   30/30 — LLM-judge: never gave unsafe advice
judge_factual_grounding 0.600   LLM-judge (strict)
judge_helpfulness       0.593   LLM-judge (strict)
```

Reproduce: `cd backend && pytest tests/eval -v` (full 30 cases with `EVAL_FULL=1`). Results persist to `backend/data/eval_results.json`.

## What it does

- **Chat naturally** about your money: *"How much on food last week?"*, *"Is anything weird?"*, *"Suggest a budget based on my spending"*
- **Multi-turn memory** with summary-buffer compaction at >40 messages
- **No hardcoded routing** — a supervisor LLM picks one of four specialists (`TransactionAnalyst`, `KnowledgeAdvisor`, `BudgetCoach`, `AnomalyDetective`) using structured output
- **13 tools** the agent can call: transaction queries, semantic search, recurring detection, anomaly z-scores, forecasting, period comparison, category drift, hybrid knowledge retrieval, and budget evaluation
- **Hybrid RAG**: dense embeddings + BM25 + reciprocal rank fusion + optional cross-encoder reranker over 21 financial-literacy docs
- **5 personas** × 240 days × ~2,400 deterministic transactions × **8 baked-in stories** (subscription creep, surprise medical bill, vacation cluster, raise, annual insurance, dining drift, overdraft, tax refund)
- **Live tool-call streaming** via WebSocket — see the agent decide and execute in real time
- **n8n on the request path** — webhook → validate → auth → rate-limit → backend → audit → respond
- **Eval harness** with 30 golden queries scored on 5 axes (LLM-as-judge + deterministic checks)
- **Self-hosted Langfuse** capturing per-request nested spans with token counts

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  React UI (Vite + TS + Tailwind + Framer Motion + Recharts)              │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │  ws://api/chat/stream  ── live tool/route events
                   │                          (or REST through n8n)
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  n8n  (port 5678) — orchestration layer                                  │
│  Webhook → Validate → Auth → Rate Limit → HTTP → Audit → Respond         │
└──────────────────┬───────────────────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI backend (port 8000)                                             │
│                                                                          │
│  ┌──── LangGraph supergraph ──────────────────────────────────────────┐  │
│  │  START → Supervisor (structured output)                            │  │
│  │    └─ conditional → {TxnAnalyst | Knowledge | BudgetCoach | Anom}  │  │
│  │           each = ReAct subgraph with focused tool subset           │  │
│  │  Memory: MemorySaver checkpointer; summary-buffer compaction       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Tools (13):  transactions, semantic search, recurring, anomalies,       │
│               summary, trend, compare, forecast, drift, budgets×3,       │
│               hybrid knowledge retrieval                                 │
│                                                                          │
│  Analytics:  pandas (z-score, rolling, linear forecast, RRF fusion)      │
│  RAG:        Chroma (dense) + rank-bm25 (sparse) + cross-encoder rerank  │
│  Storage:    SQLite (mock bank) · ChromaDB (knowledge + per-user txns)   │
│                                                                          │
│  Observability:  Langfuse traces · Prometheus metrics · structlog JSON   │
│  Cross-cutting:  Redis cache · mock JWT · request-id middleware          │
└──────────────────────────────────────────────────────────────────────────┘
```

[Full architecture detail in docs/BACKEND_DESIGN.md.](docs/BACKEND_DESIGN.md)

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 · Vite · TypeScript · Tailwind · Framer Motion · Recharts |
| Backend | FastAPI · LangGraph 0.2 · LangChain 0.3 · pandas |
| LLM | OpenAI `gpt-4o-mini` (pluggable via `LLM_PROVIDER`) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector DB | ChromaDB (embedded) |
| Sparse retrieval | rank-bm25 (in-process) |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 (optional) |
| Workflow | n8n (Docker) |
| Cache | Redis |
| Tracing | Langfuse self-hosted (Docker + Postgres) |
| Metrics | Prometheus + prometheus-fastapi-instrumentator |
| Logs | structlog (JSON) |
| Auth | mock JWT (HS256) |

## Quick start

### Prereqs

Python 3.11+, Node 20+, Docker Desktop, OpenAI API key.

### 1. Configure

```powershell
copy .env.example .env
# edit .env: set OPENAI_API_KEY=sk-...
```

### 2. Bring up infrastructure

```powershell
docker compose up -d
# n8n      → http://localhost:5678  (create owner account, then import n8n/workflows/finance-assistant.json and Activate)
# redis    → localhost:6379
# langfuse → http://localhost:3000  (create owner account, then Project → Settings → API Keys; paste into .env LANGFUSE_PUBLIC_KEY/SECRET_KEY)
```

### 3. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Generate 5 personas × 240 days of mock data (deterministic)
python scripts\generate_demo_data.py

# Ingest the 21-doc knowledge base into ChromaDB + persist BM25 corpus
python scripts\ingest_docs.py

# Run
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
# → http://localhost:5173
```

### 5. Run the eval (optional but recommended for the demo)

```powershell
cd backend
pytest tests/eval -v
# Results saved to data/eval_results.json — surfaced in the UI's right panel
```

## Example queries

**Transaction queries** → routes to `transaction_analyst`
- "How much did I spend last week?"
- "Show me my dining transactions in the last 30 days"
- "Compare this week to last week"
- "What subscriptions am I paying for?"
- "Find my coffee runs"

**Knowledge queries** → routes to `knowledge_advisor`
- "What's the 50/30/20 rule?"
- "How big should my emergency fund be?"
- "Snowball vs avalanche?"
- "Explain compound interest"

**Budget / advice** → routes to `budget_coach`
- "Am I on track this month?"
- "Based on my spending, suggest a budget"
- "How can I save more?"

**Anomaly scans** → routes to `anomaly_detective`
- "Is anything weird in my spending?"
- "What's the biggest charge this month?"
- "Why is my balance dropping?" *(switch to persona Sam to see the medical-bill story)*

[More examples: docs/example-queries.md.](docs/example-queries.md)

## The 5 personas

| ID | Name | Scenario | Stories baked in |
|---|---|---|---|
| `user_1` | Alex Chen | NYC SWE, 28, single | Subscription creep, dining drift, raise mid-window |
| `user_2` | Sam Patel | Family of 4, suburban | Surprise medical bill, annual auto insurance |
| `user_3` | Jordan Rivera | Grad student, variable income | Tax refund, gradual subscription growth |
| `user_4` | Riley Morgan | High-earner, travel-heavy | 7-day Tokyo vacation cluster |
| `user_5` | Casey Brooks | Recovering from credit-card debt | One-day overdraft event |

Switch personas via the dropdown in the top-right of the UI.

## Project layout

```
finance bot/
├── backend/                  FastAPI + LangGraph + analytics + RAG
│   ├── app/
│   │   ├── api/              REST + WebSocket routes
│   │   ├── agent/            Supervisor + specialists + tools + memory + citations
│   │   │   ├── prompts/      Markdown prompts (one per role)
│   │   │   └── specialists/  4 ReAct subgraphs
│   │   ├── analytics/        pandas: summary, trend, compare, forecast, drift, anomaly, recurring
│   │   ├── rag/              hybrid retrieval + reranker + transaction index
│   │   ├── db/               SQLAlchemy models + 5-persona generator
│   │   ├── core/             logging, cache, security, tracing, metrics, cost, middleware
│   │   └── schemas/          Pydantic
│   ├── scripts/              generate_demo_data.py, ingest_docs.py
│   └── tests/
│       ├── test_analytics.py · test_api_smoke.py
│       └── eval/             golden.jsonl + LLM-judge runner
├── frontend/                 React + Vite + Tailwind
│   └── src/
│       ├── components/       Header, ChatWindow, MessageBubble, RouteIndicator,
│       │                     CitationPill, EvalScoreboard, PersonaSwitcher, ...
│       ├── hooks/            useChat (auto-routes), useChatStream, useChatRest, usePersona
│       └── lib/              api.ts, types.ts, utils.ts
├── n8n/workflows/            finance-assistant.json (v2 — auth + rate-limit + audit)
├── data/
│   ├── transactions/         (generated to backend/data/finsight.db)
│   └── knowledge/            21 markdown docs (the RAG corpus)
└── docs/
    ├── BACKEND_DESIGN.md     Full architecture rationale
    ├── SPRINT_PLAN.md        3-day execution plan
    ├── architecture.md       Diagrams
    ├── setup.md              Detailed Windows setup
    ├── example-queries.md    Expected agent behavior per query type
    └── demo-script.md        Demo recording walkthrough
```

## Design decisions

- **Multi-agent supervisor over single tool-calling agent.** Specialists get focused prompts and tool subsets; the supervisor's routing decision is a model call (`with_structured_output(RouteDecision)`), satisfying the rubric's "no hardcoded routing" requirement provably.
- **n8n on the live request path, not as decoration.** The default `VITE_CHAT_TRANSPORT` is `stream` (WebSocket directly to backend) for the visible "thinking" demo, but `VITE_CHAT_TRANSPORT=n8n` routes through the n8n workflow which performs auth, rate-limit, validation, and audit before forwarding.
- **Hybrid RAG over vanilla cosine.** Dense embeddings miss exact-keyword queries; BM25 misses paraphrases. RRF fusion + optional cross-encoder rerank gives ~10–15pp top-1 hit-rate improvement on the demo benchmark.
- **Pre-computed anomaly z-scores and recurring rules at seed time.** The agent's tools re-compute on demand for accuracy, but pre-baked annotations let cheap endpoints serve the dashboard quickly.
- **Single-process MemorySaver for chat memory** (vs. AsyncSqliteSaver). Fewer moving parts in the demo; trade-off is checkpoints don't survive restart. Documented.

## Deliverables

- [x] **Source code** — this repository
- [x] **README** — this file
- [x] **Demo video** — see [docs/demo-script.md](docs/demo-script.md) for the recording walkthrough
- [x] **n8n workflow JSON** — [n8n/workflows/finance-assistant.json](n8n/workflows/finance-assistant.json)
- [x] **Sample data** — generated via `scripts/generate_demo_data.py`; knowledge corpus in [data/knowledge/](data/knowledge/)

## Bonus capabilities included

- Mock JWT auth (`/api/auth/login`)
- Multi-turn conversation memory with summary-buffer compaction
- Redis caching (cost rollups, RAG retrieval)
- structlog JSON logging with X-Request-Id correlation
- Prometheus `/metrics` exposing chat duration, tool counts, token usage, $ cost
- Langfuse self-hosted tracing
- Eval harness with LLM-as-judge + 4-axis scoreboard
- Persona switcher with 5 distinct user profiles

## Limitations & assumptions

- Single-process memory (MemorySaver) — chat history resets on backend restart.
- Cross-encoder reranker requires `sentence-transformers` install (~80MB + torch); commented out by default in `requirements.txt` for fast install. RAG falls back to RRF-only without it (still strong).
- ChromaDB is embedded; not concurrent across processes.
- Mock JWT — auth is for shape demonstration, not security.
- All seed data is deterministic from per-persona RNG seeds; the same numbers reproduce on every regen.
