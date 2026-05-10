import { motion } from "framer-motion";
import { ChevronDown, Cog, Database, Search, TrendingUp } from "lucide-react";
import { useState } from "react";

import type { ToolCallTrace } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  traces: ToolCallTrace[];
}

const ICONS: Record<string, React.ReactNode> = {
  get_transactions: <Database className="h-3.5 w-3.5" />,
  get_spending_summary: <TrendingUp className="h-3.5 w-3.5" />,
  get_spending_trend: <TrendingUp className="h-3.5 w-3.5" />,
  search_financial_knowledge: <Search className="h-3.5 w-3.5" />,
};

/** Tools return `{ "_summary": "...", ...other fields }`. The summary is
 * a one-line human description we surface here. Falls back to a short
 * preview if no summary present. */
function readableResult(raw: string | undefined): string {
  if (!raw) return "";
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) return trimmed.slice(0, 240);
  // Try strict parse first
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object") {
      if (typeof parsed._summary === "string" && parsed._summary)
        return parsed._summary;
      const keys = Object.keys(parsed).filter((k) => k !== "_summary").slice(0, 4);
      const previews = keys.map((k) => {
        const v = parsed[k];
        if (Array.isArray(v)) return `${k}: ${v.length} item(s)`;
        if (typeof v === "object" && v !== null) return `${k}: …`;
        return `${k}: ${String(v).slice(0, 40)}`;
      });
      return previews.join(" · ");
    }
  } catch {
    /* JSON likely truncated mid-string - fall through to regex */
  }
  // Regex fallback: extract _summary even from truncated JSON. Handles
  // backslash-escaped quotes and stops at the first unescaped quote.
  const m = trimmed.match(/"_summary"\s*:\s*"((?:[^"\\]|\\.)*)"/);
  if (m && m[1]) {
    return m[1].replace(/\\"/g, '"').replace(/\\\\/g, "\\");
  }
  return trimmed.slice(0, 240);
}

function readableArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => {
      if (typeof v === "string") return `${k}="${v}"`;
      if (typeof v === "number" || typeof v === "boolean") return `${k}=${v}`;
      return `${k}=…`;
    });
  return entries.length ? `(${entries.join(", ")})` : "()";
}

/** Compact single-line label for the collapsible header.
 * - 1 tool   → "agent → tool"
 * - 2 tools  → "agent → tool1 → tool2"
 * - 3+ tools → "agent · 16 steps · 4 tools" (never wraps, even with 50 calls) */
function compactLabel(traces: ToolCallTrace[]): string {
  if (traces.length === 0) return "agent";
  if (traces.length <= 2) {
    return `agent → ${traces.map((t) => t.name).join(" → ")}`;
  }
  const uniqueTools = new Set(traces.map((t) => t.name)).size;
  const stepWord = traces.length === 1 ? "step" : "steps";
  const toolWord = uniqueTools === 1 ? "tool" : "tools";
  return `agent · ${traces.length} ${stepWord} · ${uniqueTools} ${toolWord}`;
}

export function ToolTrace({ traces }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition px-2 py-1 rounded-md border border-slate-200 bg-slate-50 whitespace-nowrap max-w-full"
        title={`agent → ${traces.map((t) => t.name).join(" → ")}`}
      >
        <Cog className="h-3.5 w-3.5 flex-shrink-0" />
        <span className="font-mono truncate">{compactLabel(traces)}</span>
        <ChevronDown
          className={cn("h-3 w-3 transition flex-shrink-0", open && "rotate-180")}
        />
      </button>

      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-2 space-y-1.5 overflow-hidden"
        >
          {traces.map((t, i) => {
            const summary = readableResult(t.result_preview);
            const argsStr = readableArgs(t.args || {});
            return (
              <div
                key={i}
                className="rounded-md bg-slate-50 border border-slate-200 border-l-4 border-l-brand-500 px-3 py-2"
              >
                <div className="flex items-center gap-2 text-xs font-mono text-brand-700">
                  {ICONS[t.name] ?? <Cog className="h-3.5 w-3.5" />}
                  <span className="font-semibold">{t.name}</span>
                  <span className="text-slate-500">{argsStr}</span>
                </div>
                {summary && (
                  <div className="mt-1 text-[11px] text-slate-600 leading-relaxed">
                    {summary}
                  </div>
                )}
              </div>
            );
          })}
        </motion.div>
      )}
    </div>
  );
}
