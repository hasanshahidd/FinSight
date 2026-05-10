import { motion } from "framer-motion";
import { History, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, Trash2 } from "lucide-react";

import type { ChatSession } from "@/hooks/useChatHistory";
import { cn } from "@/lib/utils";

interface Props {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

function groupByDate(sessions: ChatSession[]): Record<string, ChatSession[]> {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const sevenDaysAgo = new Date(today);
  sevenDaysAgo.setDate(today.getDate() - 7);

  const buckets: Record<string, ChatSession[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };

  for (const s of sessions) {
    const updated = new Date(s.updatedAt);
    if (updated >= today) buckets.Today.push(s);
    else if (updated >= yesterday) buckets.Yesterday.push(s);
    else if (updated >= sevenDaysAgo) buckets["Previous 7 days"].push(s);
    else buckets.Older.push(s);
  }

  return buckets;
}

export function ChatHistorySidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
  collapsed,
  onToggleCollapse,
}: Props) {
  if (collapsed) {
    return (
      <div className="w-12 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col items-center py-3 gap-3">
        <button
          onClick={onToggleCollapse}
          title="Show history"
          className="h-8 w-8 rounded-md hover:bg-slate-100 grid place-items-center text-slate-500 hover:text-slate-900 transition"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </button>
        <button
          onClick={onNew}
          title="New chat"
          className="h-8 w-8 rounded-md bg-brand-600 hover:bg-brand-700 grid place-items-center text-white transition"
        >
          <Plus className="h-4 w-4" />
        </button>
        {sessions.length > 0 && (
          <div className="text-[10px] text-slate-400 mt-2 flex items-center" title={`${sessions.length} chats`}>
            <History className="h-3 w-3" />
          </div>
        )}
      </div>
    );
  }

  const groups = groupByDate(sessions);

  return (
    <aside className="w-72 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col">
      <div className="flex items-center gap-2 p-3 border-b border-slate-200">
        <button
          onClick={onNew}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
        <button
          onClick={onToggleCollapse}
          title="Collapse history"
          className="h-9 w-9 rounded-lg border border-slate-200 hover:bg-slate-100 grid place-items-center text-slate-500 hover:text-slate-900 transition flex-shrink-0"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        {sessions.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <MessageSquare className="h-6 w-6 text-slate-300 mx-auto mb-2" />
            <p className="text-xs text-slate-500">
              No conversations yet. Start one above.
            </p>
          </div>
        ) : (
          Object.entries(groups).map(([label, items]) =>
            items.length === 0 ? null : (
              <div key={label} className="mb-4">
                <div className="px-2 mb-1 text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                  {label}
                </div>
                <ul className="space-y-0.5">
                  {items.map((s) => (
                    <motion.li
                      key={s.id}
                      initial={{ opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={cn(
                        "group flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition",
                        activeId === s.id
                          ? "bg-brand-50 text-brand-700"
                          : "text-slate-700 hover:bg-slate-100",
                      )}
                      onClick={() => onSelect(s.id)}
                    >
                      <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
                      <span className="flex-1 text-sm truncate">{s.title}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm("Delete this conversation?")) onDelete(s.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-100 hover:text-red-600 transition"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </motion.li>
                  ))}
                </ul>
              </div>
            ),
          )
        )}
      </div>

      <div className="p-3 border-t border-slate-200 text-[11px] text-slate-400 text-center">
        History is stored locally in your browser
      </div>
    </aside>
  );
}
