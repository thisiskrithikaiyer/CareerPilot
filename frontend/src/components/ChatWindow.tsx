"use client";

import { useState, useRef, useEffect } from "react";
import { Message, AgentEvent, sendMessage, fetchChatHistory, AuthError } from "@/lib/api";
import ChatBubble from "./ChatBubble";

// Format agent id → display name  e.g. "job_search_coach" → "Job Search Coach"
function formatAgent(raw: string) {
  return raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

type ChatItem =
  | { kind: "message"; message: Message }
  | { kind: "handoff"; agent: string; id: string };

interface Props {
  pendingMessage?: string;
  onFirstMessage?: () => void;
  onPendingConsumed?: () => void;
  onHistoryLoaded?: () => void;
  onAuthError?: () => void;
  onAgentEvents?: (events: AgentEvent[]) => void;
  onLoadingChange?: (loading: boolean) => void;
}

export default function ChatWindow({
  pendingMessage,
  onFirstMessage,
  onPendingConsumed,
  onHistoryLoaded,
  onAuthError,
  onAgentEvents,
  onLoadingChange,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [items, setItems] = useState<ChatItem[]>([]);
  const [currentAgent, setCurrentAgent] = useState<string | undefined>();
  const [chips, setChips] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchChatHistory(10).then((history) => {
      if (history.length > 0) {
        setMessages(history);
        setItems(history.map((m) => ({ kind: "message", message: m })));
        onHistoryLoaded?.();
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items, chips, loading]);

  useEffect(() => {
    if (pendingMessage) {
      handleSend(pendingMessage);
      onPendingConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingMessage]);

  async function handleSend(text?: string) {
    const msgText = (text ?? input).trim();
    if (!msgText || loading) return;

    const isFirst = messages.length === 0;
    const userMsg: Message = { role: "user", content: msgText };
    const updatedMessages = [...messages, userMsg];

    setMessages(updatedMessages);
    setItems((prev) => [...prev, { kind: "message", message: userMsg }]);
    setChips([]);
    setInput("");
    setLoading(true);
    onLoadingChange?.(true);
    setError(null);

    if (isFirst) onFirstMessage?.();

    try {
      const res = await sendMessage(updatedMessages);
      const agent = res.agent;
      const assistantMsg: Message = { role: "assistant", content: res.reply };

      if (res.agent_events?.length) {
        onAgentEvents?.(res.agent_events);
      }

      setMessages([...updatedMessages, assistantMsg]);
      setChips(res.chips ?? []);

      setItems((prev) => {
        const next: ChatItem[] = [...prev];
        // Insert handoff divider if agent changed
        if (agent && agent !== currentAgent) {
          next.push({ kind: "handoff", agent, id: `handoff-${Date.now()}` });
          setCurrentAgent(agent);
        }
        next.push({ kind: "message", message: assistantMsg });
        return next;
      });
    } catch (e) {
      if (e instanceof AuthError) { onAuthError?.(); return; }
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 bg-gray-50">
        {items.length === 0 && (
          <p className="text-center text-gray-400 mt-10 text-xs leading-relaxed px-2">
            Hi, I&apos;m CrisisCoach.<br />What are you working toward?
          </p>
        )}

        {items.map((item, i) =>
          item.kind === "handoff" ? (
            <div key={item.id} className="flex items-center gap-2 my-4 px-1">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs text-gray-400 font-medium whitespace-nowrap px-2 py-1 bg-white border border-gray-200 rounded-full shadow-sm">
                {formatAgent(item.agent)} is with you
              </span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>
          ) : (
            <ChatBubble key={i} message={item.message} />
          )
        )}

        {loading && (
          <div className="flex justify-start mb-1">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-3 py-2 text-xs text-gray-400 shadow-sm">
              Thinking…
            </div>
          </div>
        )}
        {error && (
          <p className="text-center text-red-400 text-xs mt-2 px-2">{error}</p>
        )}

        {chips.length > 0 && !loading && (
          <div className="flex flex-wrap gap-2 mt-3 mb-1 pl-1">
            {chips.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="inline-flex items-center px-3 py-1.5 rounded-full border border-violet-400 bg-white text-xs text-violet-700 font-medium hover:bg-violet-700 hover:text-white hover:border-violet-700 transition-all shadow-sm"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3 flex gap-2 shrink-0 bg-white">
        <textarea
          className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent placeholder-gray-400 text-gray-800 transition"
          rows={2}
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          className="bg-gray-900 hover:bg-gray-700 active:bg-gray-800 disabled:opacity-30 text-white rounded-lg px-3 py-2 text-xs font-semibold transition-colors shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  );
}
