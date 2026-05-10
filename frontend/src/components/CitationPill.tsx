import { BookOpen } from "lucide-react";
import { useState } from "react";

import type { Citation } from "@/lib/types";

interface Props {
  citation: Citation;
  index: number;
}

export function CitationPill({ citation, index }: Props) {
  const [hover, setHover] = useState(false);
  const label = citation.source
    ? citation.source.replace(/-/g, " ").replace(/\.md$/, "")
    : `chunk #${index + 1}`;

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-brand-50 border border-brand-200 text-brand-700 font-mono cursor-default">
        <BookOpen className="h-2.5 w-2.5" />
        {label}
      </span>

      {hover && citation.preview && (
        <div className="absolute z-30 bottom-full mb-2 left-0 w-80 rounded-lg bg-white border border-slate-200 shadow-elevated p-3 pointer-events-none">
          <div className="flex items-center gap-1.5 mb-1.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
            <BookOpen className="h-3 w-3 text-brand-600" />
            {label}
            {citation.chunk != null && (
              <span className="text-slate-400">· chunk {citation.chunk}</span>
            )}
          </div>
          <div className="text-[11px] text-slate-600 leading-relaxed line-clamp-6">
            {citation.preview}
          </div>
        </div>
      )}
    </span>
  );
}
