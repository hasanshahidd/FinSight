import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchSuggestionsContext, type SuggestionsContext } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  query: string;
  visible: boolean;
  highlightIndex: number;
  onSelect: (text: string) => void;
  onMatchesChange: (matches: string[]) => void;
}

/** Templates with `{category}` and `{merchant}` placeholders. The autocomplete
 * fetches the user's top categories + merchants once on mount and expands
 * these templates into concrete suggestions like "How much have I spent at
 * Costco?". Filter is plain case-insensitive substring match. */
const TEMPLATES = {
  starters: [
    "Am I over budget this month?",
    "What's draining my account?",
    "Compare my spending this month vs last month",
    "What's the 50/30/20 rule?",
    "Suggest a budget for me based on my spending",
    "Find unusual transactions",
    "What are my top spending categories?",
    "How big should my emergency fund be?",
    "Is anything weird in my recent spending?",
    "How can I save more each month?",
  ],
  withCategory: [
    "How much did I spend on {category} this month?",
    "Show me my {category} transactions",
    "What's my {category} drift over the last 60 days?",
    "Cap my {category} budget",
    "Find outliers in my {category} category",
  ],
  withMerchant: [
    "How much have I spent at {merchant}?",
    "Show me my {merchant} charges",
    "Show me my recent {merchant} purchases",
  ],
  concepts: [
    "What is compound interest?",
    "Explain a high-yield savings account",
    "Snowball vs avalanche debt payoff",
    "What is FIRE?",
    "What is lifestyle creep?",
    "Explain zero-based budgeting",
    "What are sinking funds?",
    "How does a credit score work?",
  ],
};

function expand(ctx: SuggestionsContext | null): string[] {
  const all: string[] = [...TEMPLATES.starters, ...TEMPLATES.concepts];
  const cats = ctx?.categories ?? [];
  const mers = ctx?.merchants ?? [];
  for (const tpl of TEMPLATES.withCategory) {
    for (const c of cats) all.push(tpl.replace("{category}", c));
  }
  for (const tpl of TEMPLATES.withMerchant) {
    for (const m of mers) all.push(tpl.replace("{merchant}", m));
  }
  return all;
}

export function ChatSuggestions({
  query,
  visible,
  highlightIndex,
  onSelect,
  onMatchesChange,
}: Props) {
  const [ctx, setCtx] = useState<SuggestionsContext | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSuggestionsContext()
      .then((c) => {
        if (!cancelled) setCtx(c);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const all = useMemo(() => expand(ctx), [ctx]);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    // Empty input -> no suggestions. Only kick in once the user starts typing.
    if (!q) return [];
    const starts: string[] = [];
    const contains: string[] = [];
    for (const s of all) {
      const lo = s.toLowerCase();
      if (lo.startsWith(q)) starts.push(s);
      else if (lo.includes(q)) contains.push(s);
    }
    return [...starts, ...contains].slice(0, 4);
  }, [all, query]);

  useEffect(() => {
    onMatchesChange(matches);
  }, [matches, onMatchesChange]);

  if (!visible || matches.length === 0) return null;

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl bg-white border border-slate-200 shadow-lg overflow-hidden z-10">
      <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-400 border-b border-slate-100 bg-slate-50">
        Suggestions
      </div>
      <ul>
        {matches.map((s, i) => (
          <li
            key={s}
            onMouseDown={(e) => {
              e.preventDefault();
              onSelect(s);
            }}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition",
              i === highlightIndex
                ? "bg-brand-50 text-brand-900"
                : "text-slate-700 hover:bg-slate-50",
            )}
          >
            <Search className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
            <span className="truncate">{highlightMatch(s, query)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Wrap the matched substring in <strong> so the user sees what they typed. */
function highlightMatch(text: string, query: string) {
  const q = query.trim();
  if (!q) return text;
  const idx = text.toLowerCase().indexOf(q.toLowerCase());
  if (idx < 0) return text;
  return (
    <>
      {text.slice(0, idx)}
      <strong className="text-brand-700">{text.slice(idx, idx + q.length)}</strong>
      {text.slice(idx + q.length)}
    </>
  );
}

export const SUGGESTION_LIMIT = 6;
