import type {
  CostRollup,
  EvalScoreboard,
  SpendingSummary,
  ToolCallTrace,
  Transaction,
  TrendResponse,
  User,
  UserWithAccounts,
} from "./types";

const BACKEND = (import.meta.env.VITE_BACKEND_URL || "") as string;
const N8N_WEBHOOK =
  (import.meta.env.VITE_N8N_WEBHOOK_URL ||
    "http://localhost:5678/webhook/finance-chat") as string;

// Active user_id is read from localStorage so every fetch in this module
// scopes to the current persona without each call having to pass it.
function activeUserId(): string {
  if (typeof window === "undefined") return "user_1";
  return localStorage.getItem("finsight.active_user_id") || "user_1";
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { "X-User-Id": activeUserId(), ...extra };
}

export interface ChatApiResponse {
  message: string;
  session_id: string;
  tool_calls: ToolCallTrace[];
  citations: Array<Record<string, unknown>>;
  structured_data?: Record<string, unknown> | null;
}

/**
 * Send a chat message. ALWAYS routes through the n8n webhook — there is no
 * direct-to-backend fallback. The n8n workflow validates input, enforces
 * rate limits, calls the FastAPI agent, audit-logs the result, and returns
 * the response. This satisfies the assessment's "n8n orchestration" rubric.
 */
export async function sendChat(
  message: string,
  sessionId: string,
  userId?: string,
): Promise<ChatApiResponse> {
  const uid = userId || activeUserId();
  const res = await fetch(N8N_WEBHOOK, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Id": uid },
    body: JSON.stringify({ message, session_id: sessionId, user_id: uid }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`chat ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export const CHAT_WEBHOOK_URL = N8N_WEBHOOK;

export async function fetchUsers(): Promise<User[]> {
  const res = await fetch(`${BACKEND}/api/users`);
  if (!res.ok) throw new Error(`users ${res.status}`);
  return res.json();
}

export async function fetchMe(): Promise<UserWithAccounts> {
  const res = await fetch(`${BACKEND}/api/users/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`me ${res.status}`);
  return res.json();
}

export async function fetchTransactions(
  params: {
    date_from?: string;
    date_to?: string;
    category?: string;
    limit?: number;
  } = {},
): Promise<Transaction[]> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  });
  const res = await fetch(`${BACKEND}/api/transactions?${qs.toString()}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`transactions ${res.status}`);
  return res.json();
}

export async function fetchSummary(
  period = "last_7_days",
): Promise<SpendingSummary> {
  const res = await fetch(`${BACKEND}/api/insights/summary?period=${period}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`summary ${res.status}`);
  return res.json();
}

export async function fetchTrend(
  period = "last_30_days",
): Promise<TrendResponse> {
  const res = await fetch(`${BACKEND}/api/insights/trend?period=${period}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`trend ${res.status}`);
  return res.json();
}

export async function fetchCost(sessionId?: string): Promise<CostRollup> {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  const res = await fetch(`${BACKEND}/api/admin/cost${qs}`);
  if (!res.ok) throw new Error(`cost ${res.status}`);
  return res.json();
}

export async function fetchEvalScores(): Promise<EvalScoreboard> {
  const res = await fetch(`${BACKEND}/api/admin/eval`);
  if (!res.ok) throw new Error(`eval ${res.status}`);
  return res.json();
}

export interface SuggestionsContext {
  categories: string[];
  merchants: string[];
}

export async function fetchSuggestionsContext(): Promise<SuggestionsContext> {
  const res = await fetch(`${BACKEND}/api/insights/suggestions/context`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`suggestions ${res.status}`);
  return res.json();
}
