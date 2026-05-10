import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { ChatWindow } from "@/components/ChatWindow";
import { useChat } from "@/hooks/useChat";
import { useChatHistory } from "@/hooks/useChatHistory";

interface Ctx {
  persona: { activeId: string };
}

export function ChatPage() {
  const { persona } = useOutletContext<Ctx>();
  const history = useChatHistory(persona.activeId);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  const chat = useChat({
    initialMessages: history.activeSession?.messages,
    sessionId: history.activeId ?? undefined,
    onMessagesChange: (msgs) => {
      // Persist after every change. Lazily create a session on first user message.
      const hasUserMsg = msgs.some((m) => m.role === "user");
      if (!hasUserMsg) return;
      if (!history.activeId) {
        history.createSession(msgs);
      } else {
        history.updateSession(history.activeId, msgs);
      }
    },
  });

  // When user switches personas, reset to a fresh chat
  useEffect(() => {
    history.selectSession(null);
    chat.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [persona.activeId]);

  const handleSend = (text: string) => chat.send(text, persona.activeId);
  const handleNew = () => {
    history.selectSession(null);
    chat.reset();
  };
  const handleSelectSession = (id: string) => {
    history.selectSession(id);
    // useChat will pick up initialMessages from the new active session via opts effect
  };

  return (
    <div className="flex-1 flex min-h-0">
      <ChatHistorySidebar
        sessions={history.sessions}
        activeId={history.activeId}
        onSelect={handleSelectSession}
        onNew={handleNew}
        onDelete={history.deleteSession}
        collapsed={historyCollapsed}
        onToggleCollapse={() => setHistoryCollapsed((v) => !v)}
      />
      <ChatWindow
        messages={chat.messages}
        sending={chat.sending}
        onSend={handleSend}
      />
    </div>
  );
}
