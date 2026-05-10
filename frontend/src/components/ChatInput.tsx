import { ArrowUp, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatSuggestions } from "./ChatSuggestions";

interface Props {
  sending: boolean;
  onSubmit: (text: string) => void;
  placeholder?: string;
}

export function ChatInput({ sending, onSubmit, placeholder }: Props) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [matches, setMatches] = useState<string[]>([]);
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const matchCount = matches.length;

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = Math.min(ref.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  // Reset highlight when match list changes
  useEffect(() => {
    setHighlight(0);
  }, [matchCount, value]);

  const submit = (text?: string) => {
    const v = (text ?? value).trim();
    if (!v || sending) return;
    onSubmit(v);
    setValue("");
  };

  const handleSelect = useCallback((text: string) => {
    setValue(text);
    ref.current?.focus();
  }, []);

  const showSuggestions = focused && !sending;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="relative"
    >
      <ChatSuggestions
        query={value}
        visible={showSuggestions}
        highlightIndex={highlight}
        onSelect={handleSelect}
        onMatchesChange={setMatches}
      />

      <div className="relative rounded-xl bg-white border border-slate-300 shadow-card focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100 transition">
        <textarea
          ref={ref}
          rows={1}
          placeholder={placeholder ?? "Ask anything about your spending or get financial advice…"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => {
            // Suggestion keyboard nav (only when suggestions are showing)
            if (showSuggestions && matchCount > 0) {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setHighlight((h) => (h + 1) % matchCount);
                return;
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                setHighlight((h) => (h - 1 + matchCount) % matchCount);
                return;
              }
              if (e.key === "Tab" && !e.shiftKey) {
                // Tab fills the highlighted suggestion without submitting
                e.preventDefault();
                const pick = matches[highlight];
                if (pick) setValue(pick);
                return;
              }
              if (e.key === "Escape") {
                e.preventDefault();
                setFocused(false);
                ref.current?.blur();
                return;
              }
            }
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          className="w-full resize-none bg-transparent px-4 py-3 pr-14 outline-none placeholder:text-slate-400 text-[15px] text-slate-900"
        />
        <button
          type="submit"
          disabled={!value.trim() || sending}
          className="absolute right-2 bottom-2 h-9 w-9 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:bg-slate-200 disabled:cursor-not-allowed grid place-items-center transition"
        >
          {sending ? (
            <Loader2 className="h-4 w-4 text-white animate-spin" />
          ) : (
            <ArrowUp className="h-4 w-4 text-white" />
          )}
        </button>
      </div>
      <p className="mt-2 text-[11px] text-slate-400 text-center">
        Press <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px]">Enter</kbd> to send,
        {" "}<kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px]">↑↓</kbd> to navigate suggestions,
        {" "}<kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px]">Tab</kbd> to fill
      </p>
    </form>
  );
}
