import { useCallback, useEffect, useState } from "react";

import { fetchUsers } from "@/lib/api";
import type { User } from "@/lib/types";

const STORAGE_KEY = "finsight.active_user_id";


export function usePersona() {
  const [users, setUsers] = useState<User[]>([]);
  const [activeId, setActiveId] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(STORAGE_KEY) || "user_1";
    }
    return "user_1";
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const all = await fetchUsers();
        if (!alive) return;
        setUsers(all);
      } catch {
        /* backend may not be up — UI degrades to default */
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const switchTo = useCallback((id: string) => {
    setActiveId(id);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, id);
    }
  }, []);

  const active = users.find((u) => u.id === activeId);

  return { users, active, activeId, switchTo, loading };
}
