# Setup Guide (Windows)

## Prerequisites

- Python 3.11+ (`python --version`)
- Node.js 20+ (`node --version`)
- Docker Desktop (for n8n + Redis)
- An OpenAI API key

## 1. Clone and configure

```powershell
git clone <repo-url> finsight
cd finsight
copy .env.example .env
# Open .env, set OPENAI_API_KEY=sk-...
```

## 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Generate mock data + ingest the knowledge base
python scripts\seed_db.py
python scripts\ingest_docs.py

# Run the API
uvicorn app.main:app --reload --port 8000
```

API will be at http://localhost:8000 - visit `/docs` for the auto-generated Swagger UI.

## 3. Frontend (in a new terminal)

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173.

## 4. n8n + Redis (in a new terminal, from project root)

```powershell
docker compose up -d
```

- n8n: http://localhost:5678 - set up your owner account, then **Workflows → Import** `n8n/workflows/finance-assistant.json` and **Activate**.
- Redis is reachable internally on `localhost:6379` for the backend cache.

## Smoke test

In the React UI, click any of the suggested-prompt chips on the left. You should see:

1. The user bubble appear, then a typing indicator.
2. The assistant message render with markdown.
3. A "agent → get_spending_summary" trace below the bubble - click to expand and see the tool args + result preview.
4. The right-side Insights panel populating with charts.

If the chat fails, check:

- `OPENAI_API_KEY` is set in `.env` (root) and that the backend can read it.
- Backend is running on :8000 (`curl http://localhost:8000/health`).
- n8n workflow is **active** (toggle in the workflow editor).
- `VITE_CHAT_TRANSPORT` matches your intent (`n8n` for the full pipeline, `backend` to bypass).

## Common issues

**`ModuleNotFoundError: app`** - run uvicorn from `backend/` directory, not the project root.

**ChromaDB telemetry warnings** - harmless; we disable telemetry in `retriever.py`.

**n8n can't reach the backend** - Docker uses `host.docker.internal` to refer to your host machine on Windows/Mac. On Linux, edit the workflow's HTTP Request node to use your LAN IP instead.

**OpenAI 401** - your API key is wrong or has no quota. The free tier requires manual top-up.
