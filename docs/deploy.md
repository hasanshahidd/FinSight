# Deployment guide

The stack is **FastAPI + ChromaDB + SQLite (backend)**, **Vite/React (frontend)**, **n8n (orchestration)**, and **Redis (cache)**. Everything is containerized - `docker compose up -d` from the repo root brings it up locally and that same compose file is the deployment unit on most hosts below.

You need only one external secret: **`OPENAI_API_KEY`**. Everything else (databases, n8n, vector store) is self-contained.

---

## Free deployment options (not Railway)

### Option 1 - Oracle Cloud Always Free (recommended for full stack)

**Why**: free *forever* (not credits), 4 ARM cores + 24GB RAM, plenty for ChromaDB embeddings and three containers.

**Steps**:
1. Sign up at https://cloud.oracle.com/free - pick the Always Free Ampere A1 shape (ARM, 4 OCPU / 24 GB).
2. Create a `VM.Standard.A1.Flex` instance with Ubuntu 22.04. Open ports **22, 80, 5173, 5678, 8000** in the security list.
3. SSH in, install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER && newgrp docker
   ```
4. Clone the repo, set the key, bring it up:
   ```bash
   git clone <your-repo> finsight && cd finsight
   echo "OPENAI_API_KEY=sk-..." > .env
   docker compose up -d
   ```
5. Point a free Cloudflare DNS at the VM's public IP (or use the IP directly).

**Access**: `http://<vm-ip>:5173` for the app, `:5678` for n8n, `:8000/docs` for API.

---

### Option 2 - Render (zero-config, free with cold starts)

**Why**: simplest. Connect GitHub, push, auto-deploy. Free web services sleep after 15 minutes idle.

| Service | Render plan | Config |
|---------|-------------|--------|
| Backend (FastAPI) | Free Web Service · Docker | Dockerfile = `backend/Dockerfile`. Add env `OPENAI_API_KEY`. Health check `/healthz`. |
| Frontend (Vite) | Free Static Site | Build cmd `cd frontend && npm ci && npm run build`. Publish dir `frontend/dist`. Env `VITE_BACKEND_URL=https://<backend>.onrender.com`, `VITE_N8N_WEBHOOK_URL=https://<n8n>.onrender.com/webhook/finance-chat`. |
| n8n | Free Web Service · Docker image `n8nio/n8n:latest` | Env `WEBHOOK_URL=https://<n8n>.onrender.com`, `N8N_PROTOCOL=https`, `N8N_HOST=<n8n>.onrender.com`. Persist with a free Render disk (1 GB). |
| Redis | Upstash free (separate) | Add `REDIS_URL=rediss://...` to backend env. |

**Note on cold starts**: first request after 15 min idle takes ~30 s. Acceptable for a demo, mention it on the README.

---

### Option 3 - Fly.io ($5/month free credit, no sleep)

**Why**: $5/month auto-grant covers a small backend + n8n machine if sized to ~256 MB. No cold starts.

```bash
brew install flyctl  # or curl -L https://fly.io/install.sh | sh
flyctl auth signup

# Backend
cd backend && flyctl launch --name finsight-backend --region iad --no-deploy
# edit fly.toml: internal_port = 8000, set [[mounts]] for data/, env OPENAI_API_KEY
flyctl secrets set OPENAI_API_KEY=sk-...
flyctl deploy

# n8n (separate app)
flyctl launch --image n8nio/n8n:latest --name finsight-n8n --no-deploy
flyctl secrets set N8N_HOST=finsight-n8n.fly.dev WEBHOOK_URL=https://finsight-n8n.fly.dev
flyctl deploy

# Frontend → Vercel or Cloudflare Pages (see below)
```

---

### Option 4 - Hugging Face Spaces (Docker SDK, 16 GB RAM free)

**Why**: 16 GB RAM is huge. Single-container, so bundle backend + n8n via supervisord or just deploy backend and put n8n elsewhere.

1. Create a new Space → SDK = **Docker**.
2. Push the repo with a `Dockerfile` at root that uses `backend/Dockerfile` as base and runs FastAPI.
3. Add `OPENAI_API_KEY` as a Space Secret.
4. The Space gets a public URL like `https://<user>-finsight.hf.space`.

n8n is harder to fit in a single Space - easier to host n8n on Render/Fly and the backend on HF Spaces.

---

### Option 5 - Cloud Run (Google) - generous, pay-per-second

**Why**: 2 million requests/month free, pay only when traffic hits. No cold start surcharge for the free tier.

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT
gcloud run deploy finsight-backend --source backend --region us-central1 \
  --allow-unauthenticated --set-env-vars OPENAI_API_KEY=sk-... \
  --memory 1Gi --cpu 1 --min-instances 0 --max-instances 3
```

n8n on Cloud Run works the same way with image `n8nio/n8n:latest`.

---

## Frontend - always deploy as a static site

Wherever the backend lives, the frontend is just a Vite-built static bundle. **Free hosts**:

| Host | Build command | Publish dir |
|------|---------------|-------------|
| **Vercel** | `cd frontend && npm ci && npm run build` | `frontend/dist` |
| **Cloudflare Pages** | same | same |
| **Netlify** | same | same |
| **GitHub Pages** | same | same (push `dist/` to `gh-pages` branch) |

Vercel + Cloudflare Pages are the smoothest for Vite projects. Both give you a free `*.vercel.app` / `*.pages.dev` subdomain immediately.

**Required env vars on the frontend host**:
```
VITE_BACKEND_URL=https://<backend-public-url>
VITE_N8N_WEBHOOK_URL=https://<n8n-public-url>/webhook/finance-chat
```

---

## Redis - soft dependency, can be skipped

Redis is used for **one thing only**: persisting token + $ cost rollups across chat requests (powers `/api/admin/cost` and the eval scoreboard's cost figures). Everything else - chat, RAG, agent memory, analytics - runs without it.

The cache layer fails gracefully: if Redis isn't reachable, [`get_redis()`](../backend/app/core/cache.py) logs one warning and `cache_get`/`cache_set` no-op. The app stays fully functional; you just don't get accumulated cost numbers.

**Free options if you want cost tracking**:
- **Upstash** - 10k commands/day, 256 MB. More than enough (the cache writes ~2 keys per chat request). https://upstash.com
- **Redis Labs** - 30 MB free. https://redis.com

**Skip Redis (recommended for a demo)**:
- Don't set `REDIS_URL` in deployed env vars (or leave it pointing at a non-existent host)
- One `redis_unavailable` warning at startup, then silent no-ops
- All visible features keep working; only the global cost rollup endpoint returns zeros

---

## Recommended free combos

### "Best uptime" combo
- Backend + n8n → **Oracle Cloud Always Free** (one VM, docker-compose)
- Frontend → **Vercel**
- Redis → in-memory (no external service)
- **Cost**: $0 forever
- **Cold start**: never

### "Zero-config" combo
- Backend → **Render Free**
- n8n → **Render Free**
- Frontend → **Vercel**
- Redis → **Upstash Free**
- **Cost**: $0
- **Cold start**: ~30 s after 15 min idle (fine for demos)

### "Fast everywhere" combo
- Backend + n8n → **Fly.io** (uses $5/mo grant)
- Frontend → **Cloudflare Pages**
- Redis → **Upstash Free**
- **Cost**: $0 if usage stays under the grant
- **Cold start**: minimal

---

## Production checklist

Before any deploy:

- [ ] `OPENAI_API_KEY` set as a secret (never committed)
- [ ] Update `frontend/.env.production` with the public backend + n8n URLs
- [ ] Update n8n's `Backend HTTP Request` node URL to your deployed backend (not `localhost:8000`)
- [ ] Set `CORS_ALLOWED_ORIGINS` in backend to your frontend domain
- [ ] If using a custom domain, point DNS, then enable HTTPS (most platforms above do this automatically)
- [ ] Run `pytest tests/eval` once after deploy to confirm the eval still passes against the deployed stack
- [ ] Set `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` so n8n's editor isn't public

---

## What the deployment exercises (assessment lens)

Deploying to a free host shows:
- Real Docker discipline (one compose, three services, all healthy)
- Configurable URLs (no hardcoded `localhost`)
- Secret hygiene (env vars, not committed)
- Cold-start handling (memory loaded once per worker)

For the assessment recording, deployment isn't strictly required - the docker-compose + ngrok flow lets a recruiter run it locally in two minutes. But a live URL in the README adds polish.
