import { AnimatePresence, motion } from "framer-motion";
import { Lightbulb } from "lucide-react";
import { useEffect, useRef } from "react";

import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "@/lib/types";

const SUGGESTED_PROMPTS = [
  "How much did I spend last week?",
  "What are my top categories this month?",
  "What's the 50/30/20 rule?",
  "Is anything weird in my recent spending?",
];

interface Props {
  messages: ChatMessage[];
  sending: boolean;
  onSend: (text: string) => void;
}

export function ChatWindow({ messages, sending, onSend }: Props) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const showSuggestions = messages.length <= 1;

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <div className="flex-1 min-w-0 flex flex-col bg-slate-50">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <MessageBubble msg={m} />
              </motion.div>
            ))}
          </AnimatePresence>

          {showSuggestions && (
            <div className="pt-4">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-3">
                <Lightbulb className="h-3.5 w-3.5" />
                Try asking
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SUGGESTED_PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => onSend(p)}
                    className="text-left px-3 py-2.5 rounded-lg bg-white border border-slate-200 hover:border-brand-400 hover:bg-brand-50 text-sm text-slate-700 transition"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-4 sm:px-8 py-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput sending={sending} onSubmit={onSend} />
        </div>
      </div>
    </div>
  );
}
