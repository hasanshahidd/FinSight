/**
 * Single chat hook. ALL chat requests route through the n8n webhook —
 * no alternative paths. This satisfies the assessment's n8n-orchestration
 * requirement: every user message goes:
 *
 *   React UI → n8n webhook → FastAPI backend agent → response back through n8n → UI
 *
 * The webhook URL is configured in `frontend/.env` as `VITE_N8N_WEBHOOK_URL`.
 */

import { useCallback, useEffect, useState } from "react";

import { sendChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { uid } from "@/lib/utils";

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi! I'm **FinSight**. Ask me about your spending, get a budget breakdown, or learn a saving strategy.",
  timestamp: new Date().toISOString(),
};

export interface UseChatOptions {
  initialMessages?: ChatMessage[];
  onMessagesChange?: (messages: ChatMessage[]) => void;
  sessionId?: string;
}

export function useChat(opts: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>(
    opts.initialMessages && opts.initialMessages.length > 0
      ? opts.initialMessages
      : [WELCOME],
  );
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(() => opts.sessionId || uid("s_"));

  // Notify parent on every message change so chat history can persist.
  useEffect(() => {
    opts.onMessagesChange?.(messages);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  // Pick up new initial messages when the active session changes.
  useEffect(() => {
    if (opts.initialMessages && opts.initialMessages.length > 0) {
      setMessages(opts.initialMessages);
    }
    if (opts.sessionId) setSessionId(opts.sessionId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.sessionId]);

  const send = useCallback(
    async (text: string, userId = "user_1") => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      const userMsg: ChatMessage = {
        id: uid("m_"),
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      const pending: ChatMessage = {
        id: uid("m_"),
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        pending: true,
      };
      setMessages((p) => [...p, userMsg, pending]);
      setSending(true);
      setError(null);

      try {
        const res = await sendChat(trimmed, sessionId, userId);
        const route = (res.structured_data as { route?: string } | undefined)?.route;
        const rationale = (res.structured_data as { rationale?: string } | undefined)
          ?.rationale;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pending.id
              ? {
                  ...m,
                  content: res.message,
                  tool_calls: res.tool_calls,
                  citations: res.citations as ChatMessage["citations"],
                  route,
                  rationale,
                  routedVia: "n8n",
                  pending: false,
                }
              : m,
          ),
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pending.id
              ? { ...m, content: `⚠️ ${msg}`, pending: false }
              : m,
          ),
        );
      } finally {
        setSending(false);
      }
    },
    [sending, sessionId],
  );

  const reset = useCallback(() => {
    setMessages([WELCOME]);
    setSessionId(uid("s_"));
    setError(null);
  }, []);

  return { messages, sending, error, send, reset, sessionId };
}
