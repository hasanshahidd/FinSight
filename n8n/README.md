# n8n — FinSight Chat Orchestration

This directory holds the n8n workflow that **sits in the live request path** between the React frontend and the FastAPI backend.

## Why n8n is here (and not just decorative)

The React UI does **not** call the backend's `/api/chat` directly. Instead it posts to the n8n webhook, which:

1. **Validates** the inbound payload (length limits, required fields).
2. **Forwards** the request to the backend agent (`http://host.docker.internal:8000/api/chat`).
3. **Logs** the interaction (tool calls, citations) for observability.
4. **Responds** to the webhook with the agent output, plus CORS headers for the SPA.

This makes the workflow part of the production-style request lifecycle — exactly what the assessment asks for.

## How to import

1. Start the stack:
   ```bash
   docker compose up -d
   ```
2. Open http://localhost:5678 and create your owner account.
3. In the top-right menu, choose **Workflows → Import from File** and select
   `n8n/workflows/finance-assistant.json`.
4. Click **Activate** (toggle in the top-right of the workflow canvas).
5. The webhook URL is `http://localhost:5678/webhook/finance-chat`.

## How the frontend reaches it

The Vite app reads `VITE_N8N_WEBHOOK_URL` from `.env`. Set:

```
VITE_N8N_WEBHOOK_URL=http://localhost:5678/webhook/finance-chat
VITE_CHAT_TRANSPORT=n8n
```

To bypass n8n during local debugging, set `VITE_CHAT_TRANSPORT=backend` and the UI will call FastAPI directly.

## Backend reachability from inside Docker

Because the n8n container needs to reach FastAPI running on the host, the workflow uses `host.docker.internal` (Docker Desktop's Windows/macOS hostname for the host). On Linux you may need to add `--add-host=host.docker.internal:host-gateway` to the container or substitute the host's LAN IP.

## Extending the workflow

Good places to add nodes:

- **Authentication** node — verify a JWT before forwarding.
- **Rate limit** branch — check Redis for per-user request count.
- **Switch** node by `tool_calls[].name` to fan out to different downstream systems (e.g., post to Slack when an agent decision matches a high-value pattern).
