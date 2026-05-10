# Demo Script - 7 minutes

Recorded sequence for the demo video. Targets the assessment rubric explicitly.

## Setup before recording

```powershell
# Terminal 1 - backend
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 2 - frontend
cd frontend
npm run dev

# Terminal 3 - Docker stack
docker compose up -d
# n8n at  http://localhost:5678
# Langfuse at  http://localhost:3000

# Terminal 4 - eval (run once before recording so scoreboard renders)
cd backend
pytest tests/eval -v
```

Open four tabs in your browser:
1. http://localhost:5173 - the app
2. http://localhost:5678 - n8n executions panel
3. http://localhost:3000 - Langfuse traces
4. http://localhost:8000/docs - Swagger (optional, if a recruiter wants to poke the API)

Pre-clear the chat in tab 1 so you start from a fresh session.

---

## 0:00 - App overview (45s)

> "This is FinSight AI - a conversational personal-finance assistant. The architecture: React frontend, FastAPI backend with a LangGraph multi-agent supergraph, hybrid RAG, n8n orchestration, and self-hosted Langfuse for tracing."

Point out:
- **Header**: persona switcher (top-right). Five demo personas - each with 240 days of seeded data and baked-in stories.
- **Left sidebar**: suggested prompts as chips.
- **Right sidebar**: live insights - spending stats, trend chart, top categories, eval scoreboard.

## 0:45 - Persona switch (45s)

Switch from **Alex Chen** (NYC SWE) to **Sam Patel** (family of 4). Show insights re-populate with Sam's data - different totals, different categories. Switch back to Alex.

> "Each persona has a deliberate scenario the agent can reason about. Alex has a creeping subscription pattern. Sam has a surprise medical bill in the dataset. Riley has a vacation. We'll see the agent surface these."

## 1:30 - Multi-turn transaction conversation (1m 30s)

Click the prompt chip "Last week's spend" or type:

**Q1**: *"How much did I spend on dining last week?"*

Watch the **route indicator** appear - `transaction_analyst` with rationale. Watch **tool calls** stream in live:
- `get_spending_summary` or `get_transactions` fires
- result preview appears under it
- final answer renders with markdown formatting

> "The agent decided which specialist and which tools - that decision is an LLM call, not a hardcoded `if/else`. You can see the route and the tool sequence right above the answer."

**Q2** (follow-up, no context restated): *"Is that more than usual?"*

> "Note I didn't say what 'that' refers to - the multi-turn memory carries the context. The agent is now pulling `compare_periods` to answer."

**Q3**: *"What's been driving the increase?"*

> "Same thread - `analyze_category_drift` should fire here, surfacing the dining drift baked into Alex's data."

## 3:00 - Knowledge / RAG query with citations (1m)

Click the chip "Budget framework" or type:

**Q4**: *"What's the 50/30/20 rule, and how would it apply to me?"*

Watch:
- Routes to `budget_coach` (combines knowledge + user data)
- Calls both `get_spending_summary` and `search_financial_knowledge`
- Final answer cites sources as **citation pills** under the message
- Hover one - it expands the source chunk preview

> "Hybrid retrieval - dense embeddings + BM25 + cross-encoder reranking - over a 21-document corpus. Each citation is anchored to the chunk it came from."

## 4:00 - Anomaly detection (45s)

Switch persona to **Sam Patel**. Type:

**Q5**: *"Is anything weird in my recent spending?"*

> "Routed to anomaly_detective. The seeded data has a $1,820 medical charge from 90 days ago, ~4 sigma above Sam's typical Health spend. The agent should surface that."

## 4:45 - n8n orchestration (1m)

Open n8n tab. Show the workflow `FinSight - Chat Orchestration v2`. Walk the nodes:

> "This isn't just a webhook - n8n is on the live request path. Webhook → input validation → JWT-style auth check → token-bucket rate limit → backend agent → audit log → respond. The frontend can route through here by setting `VITE_CHAT_TRANSPORT=n8n`."

Click the **Executions** tab - show the recent invocation we just made (or trigger one by switching transport and sending a message). Open one execution to show the data flowing through each node.

## 5:45 - Langfuse trace (45s)

Open Langfuse tab. Click into a recent chat trace.

> "Every chat call produces a nested trace - supervisor span, then specialist span, then each tool span with token counts and latency. This is what production observability looks like for an LLM app."

Drill into one tool call to show input/output and timing.

## 6:30 - Eval scoreboard + close (30s)

Back in the app. Point at the eval scoreboard in the right panel:

> "30 golden queries, scored on 5 axes - routing accuracy, tool coverage, factual grounding, helpfulness, safety. LLM-as-judge does the qualitative scoring; deterministic checks do the routing/tool axes. Run with `pytest tests/eval`."

Close:

> "Architecture decisions: multi-agent supervisor for clean tool-set scoping with model-decided routing; hybrid RAG because dense alone misses keyword queries; n8n on the live path so the orchestration story is real, not cosmetic. Source on GitHub, README has full setup."

---

## Backup slides if anything fails live

- If WebSocket fails → set `VITE_CHAT_TRANSPORT=n8n` and reload, falls back to REST through n8n.
- If OpenAI rate-limits → stop, wait 30s, restart. The seed data is deterministic so re-runs match.
- If Langfuse hasn't been logged into → keys not in `.env`; show the trace JSON via `/api/admin/cost` instead.

## Things to NOT cover (out of time)

- Internal pandas analytics implementation
- Specific docker-compose services beyond what's visible
- LangChain version internals
- "Why not LangChain agents instead of LangGraph" - this question kills 2 min

Keep it to 7 ± 1 minutes.
