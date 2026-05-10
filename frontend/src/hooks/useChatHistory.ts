import { useCallback, useEffect, useState } from "react";

import type { ChatMessage } from "@/lib/types";
import { uid } from "@/lib/utils";

const STORAGE_KEY = "finsight.chats";

export interface ChatSession {
  id: string;
  title: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

interface ChatStore {
  [id: string]: ChatSession;
}

function load(): ChatStore {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function save(store: ChatStore) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function deriveTitle(messages: ChatMessage[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return "New chat";
  return firstUser.content.slice(0, 50) + (firstUser.content.length > 50 ? "…" : "");
}

export function useChatHistory(activeUserId: string) {
  const [store, setStore] = useState<ChatStore>(() => load());
  const [activeId, setActiveId] = useState<string | null>(null);

  const refresh = useCallback(() => setStore(load()), []);

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) refresh();
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [refresh]);

  const sessionsForUser = Object.values(store)
    .filter((s) => s.userId === activeUserId)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  const activeSession = activeId ? store[activeId] : null;

  const createSession = useCallback(
    (initialMessages: ChatMessage[] = []): ChatSession => {
      const now = new Date().toISOString();
      const id = uid("c_");
      const session: ChatSession = {
        id,
        title: deriveTitle(initialMessages) || "New chat",
        userId: activeUserId,
        createdAt: now,
        updatedAt: now,
        messages: initialMessages,
      };
      const next = { ...store, [id]: session };
      setStore(next);
      save(next);
      setActiveId(id);
      return session;
    },
    [activeUserId, store],
  );

  const updateSession = useCallback(
    (id: string, messages: ChatMessage[]) => {
      const existing = store[id];
      if (!existing) return;
      const updated: ChatSession = {
        ...existing,
        messages,
        title: deriveTitle(messages) || existing.title,
        updatedAt: new Date().toISOString(),
      };
      const next = { ...store, [id]: updated };
      setStore(next);
      save(next);
    },
    [store],
  );

  const deleteSession = useCallback(
    (id: string) => {
      const next = { ...store };
      delete next[id];
      setStore(next);
      save(next);
      if (activeId === id) setActiveId(null);
    },
    [activeId, store],
  );

  const selectSession = useCallback((id: string | null) => {
    setActiveId(id);
  }, []);

  return {
    sessions: sessionsForUser,
    activeId,
    activeSession,
    createSession,
    updateSession,
    deleteSession,
    selectSession,
  };
}
