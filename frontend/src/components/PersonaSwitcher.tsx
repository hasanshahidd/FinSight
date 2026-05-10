import { Check, ChevronDown, Users } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { User } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  users: User[];
  activeId: string;
  onSelect: (id: string) => void;
  loading?: boolean;
  onBlueBackground?: boolean;
}

export function PersonaSwitcher({
  users,
  activeId,
  onSelect,
  loading,
  onBlueBackground,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  const active = users.find((u) => u.id === activeId);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const triggerStyles = onBlueBackground
    ? "bg-white/10 hover:bg-white/20 text-white border-white/20"
    : "bg-white hover:bg-slate-50 text-slate-700 border-slate-200";

  const iconColor = onBlueBackground ? "text-white" : "text-brand-600";
  const chevronColor = onBlueBackground ? "text-white/60" : "text-slate-400";

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={loading}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm font-medium transition disabled:opacity-50",
          triggerStyles,
        )}
      >
        <Users className={cn("h-3.5 w-3.5", iconColor)} />
        <span>{active ? active.name : "Loading…"}</span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition", chevronColor, open && "rotate-180")}
        />
      </button>

      {open && users.length > 0 && (
        <div className="absolute right-0 mt-2 w-72 rounded-xl bg-white border border-slate-200 shadow-elevated overflow-hidden z-50">
          <div className="px-3 py-2.5 border-b border-slate-100">
            <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              Switch persona
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Each persona has distinct seeded data.
            </div>
          </div>
          <ul className="max-h-80 overflow-y-auto">
            {users.map((u) => (
              <li key={u.id}>
                <button
                  onClick={() => {
                    onSelect(u.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-slate-50 transition",
                    u.id === activeId && "bg-brand-50",
                  )}
                >
                  <div className="h-7 w-7 rounded-full bg-brand-600 grid place-items-center text-[11px] font-semibold text-white flex-shrink-0 mt-0.5">
                    {u.name.slice(0, 1)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                      {u.name}
                      {u.id === activeId && <Check className="h-3 w-3 text-brand-600" />}
                    </div>
                    <div className="text-[11px] text-slate-500 line-clamp-2 leading-snug mt-0.5">
                      {u.description}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
