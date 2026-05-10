import { ChevronDown, Database, FileText, Workflow } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

export function DataSourcesPanel() {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-100 transition"
      >
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <Database className="h-3 w-3" />
          Data sources
        </div>
        <ChevronDown
          className={cn("h-3 w-3 text-slate-400 transition", open && "rotate-180")}
        />
      </button>
      {open && (
        <div className="px-3 py-2.5 space-y-2.5 text-[11px] border-t border-slate-200">
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Database className="h-3 w-3 text-brand-600" />
              Mock Banking → SQLite
            </div>
            <p className="text-slate-500 mt-0.5 leading-snug">
              5 personas · 2,763 transactions · 240-day history. Generated
              deterministically - no real bank data.
            </p>
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <FileText className="h-3 w-3 text-brand-600" />
              Knowledge Base → ChromaDB
            </div>
            <p className="text-slate-500 mt-0.5 leading-snug">
              21 markdown docs · 131 chunks · hybrid retrieval (dense embeddings
              + BM25 sparse).
            </p>
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Workflow className="h-3 w-3 text-brand-600" />
              Chat path → n8n workflow
            </div>
            <p className="text-slate-500 mt-0.5 leading-snug">
              Every chat message goes through n8n (validate → rate-limit →
              backend → audit). No direct-to-backend fallback.
            </p>
          </div>
          <div className="pt-1 border-t border-slate-200">
            <div className="text-slate-500">
              Agent decides which DB to query via LLM tool-calling - no
              hardcoded routing.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
