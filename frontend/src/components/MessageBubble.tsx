import { Bot, User, Workflow } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CitationPill } from "./CitationPill";
import { RouteIndicator } from "./RouteIndicator";
import { ToolTrace } from "./ToolTrace";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  msg: ChatMessage;
}

/** Markdown pre-processor for assistant message rendering:
 *
 * 1. **Pair unclosed bold per line.** When a paragraph contains an odd
 *    number of `**` markers, the unmatched marker would render as a
 *    literal asterisk. We append a closing `**` to any line with an odd
 *    count so `<strong>` always renders cleanly.
 * 2. **Convert citation brackets to a custom link form.** Citations are
 *    written inline as `[emergency-fund]` (a hyphenated source-stem).
 *    Markdown leaves these as plain text since it isn't a valid link, so
 *    we rewrite them to `[emergency-fund](#cite:emergency-fund)` and the
 *    `a` component override below renders the result as a small inline
 *    chip. The pattern requires a hyphen so normal bracketed text isn't
 *    accidentally restyled. */
function sanitizeMarkdown(text: string): string {
  return text
    .split("\n")
    .map((line) => {
      const count = (line.match(/\*\*/g) || []).length;
      const closed = count % 2 === 1 ? line + "**" : line;
      return closed.replace(
        /\[([a-z0-9]+(?:-[a-z0-9]+)+)\]/g,
        (_m, name) => `[${name}](#cite:${name})`,
      );
    })
    .join("\n");
}

export function MessageBubble({ msg }: Props) {
  const isUser = msg.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "h-8 w-8 rounded-lg grid place-items-center flex-shrink-0 mt-0.5",
          isUser ? "bg-brand-600" : "bg-slate-100 border border-slate-200",
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-brand-600" />
        )}
      </div>

      <div className={cn("max-w-[85%] min-w-0", isUser && "items-end")}>
        {!isUser && (msg.route || (msg.tool_calls && msg.tool_calls.length > 0)) && (
          <div className="mb-2 space-y-2">
            {msg.route && (
              <RouteIndicator route={msg.route} rationale={msg.rationale} />
            )}
            {msg.tool_calls && msg.tool_calls.length > 0 && (
              <ToolTrace traces={msg.tool_calls} />
            )}
          </div>
        )}

        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed",
            isUser
              ? "bg-brand-600 text-white"
              : "bg-white border border-slate-200 text-slate-900 shadow-card",
          )}
        >
          {msg.pending && !msg.content ? (
            <TypingIndicator />
          ) : isUser ? (
            <span className="whitespace-pre-wrap">{msg.content}</span>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ href, children, ...props }) => {
                    if (typeof href === "string" && href.startsWith("#cite:")) {
                      return (
                        <span className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[10px] font-mono bg-brand-50 text-brand-700 border border-brand-200 align-baseline">
                          {children}
                        </span>
                      );
                    }
                    return (
                      <a href={href} {...props}>
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {sanitizeMarkdown(msg.content)}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && msg.citations && msg.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {msg.citations.map((c, i) => (
              <CitationPill key={`${c.source}-${i}`} citation={c} index={i} />
            ))}
          </div>
        )}

        {!isUser && msg.routedVia === "n8n" && !msg.pending && (
          <div className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400 font-mono">
            <Workflow className="h-2.5 w-2.5" />
            routed via n8n workflow
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-1 py-1">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </span>
  );
}
