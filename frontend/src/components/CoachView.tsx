"use client";

import { useState, useEffect, useRef } from "react";
import { Message, AgentEvent, streamChat, fetchChatHistory, fetchGoalPlan, fetchTodayPlan, generatePlan, AuthError } from "@/lib/api";

const FALLBACK_GREETING =
  "Hey — your plan is ready. Ask me anything about today's goals, your strategy, or how you're feeling. I'm right here.";

function useTypewriter(text: string, speed = 16) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (ref.current) clearInterval(ref.current);
    setDisplayed("");
    setDone(false);
    if (!text) return;
    let i = 0;
    ref.current = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) { clearInterval(ref.current!); setDone(true); }
    }, speed);
    return () => { if (ref.current) clearInterval(ref.current); };
  }, [text, speed]);

  return { displayed, done };
}

interface Props {
  sessionDate: string;
  onAuthError: () => void;
  onAgentEvents: (evs: AgentEvent[]) => void;
  onLoadingChange: (v: boolean) => void;
  onCommitted?: () => void;
}

export default function CoachView({ sessionDate, onAuthError, onAgentEvents, onLoadingChange, onCommitted }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentCoachText, setCurrentCoachText] = useState(FALLBACK_GREETING);
  const [userEcho, setUserEcho] = useState("");
  const [agentLabel, setAgentLabel] = useState("CrisisCoach");
  const [chips, setChips] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { displayed, done } = useTypewriter(currentCoachText, loading ? 0 : 16);

  useEffect(() => {
    Promise.all([fetchGoalPlan(), fetchTodayPlan(sessionDate), fetchChatHistory(6)]).then(
      ([goalPlan, todayPlan, history]) => {
        if (history.length > 0) setMessages(history);

        let greeting = FALLBACK_GREETING;

        if (goalPlan?.goal_committed_at) {
          const start = new Date(goalPlan.goal_committed_at + "T00:00:00");
          const current = new Date(sessionDate + "T00:00:00");
          const dayNum = Math.max(1, Math.floor((current.getTime() - start.getTime()) / 86_400_000) + 1);
          const dt = goalPlan.goal_stratergy.daily_targets;

          if (todayPlan?.coach_note) {
            greeting = `Hi, I'm your Coach. Day ${dayNum} — ${todayPlan.coach_note}`;
          } else {
            greeting =
              `Hi, I'm your Coach. Day ${dayNum} — today's targets: ` +
              `${dt.applications} applications, ${dt.networking_messages} networking messages, ` +
              `${dt.leetcode_problems} LeetCode problems. Let's go.`;
          }
        }

        setCurrentCoachText(greeting);
      }
    );
  }, [sessionDate]);

  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    const userMsg: Message = { role: "user", content: msg };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setUserEcho(msg);
    setChips([]);
    setInput("");
    setLoading(true);
    setError(null);
    onLoadingChange(true);
    setCurrentCoachText("");
    try {
      await streamChat(updated, (ev) => {
        if (ev.type === "agent_event") {
          onAgentEvents([{
            agent: ev.agent!,
            display_name: ev.display_name!,
            reason: ev.reason!,
            timestamp: ev.timestamp!,
          } as AgentEvent]);
          setAgentLabel(ev.display_name!);
        } else if (ev.type === "done") {
          setAgentLabel(ev.agent || "CrisisCoach");
          setChips(ev.chips ?? []);
          setMessages([...updated, { role: "assistant", content: ev.reply ?? "" }]);
          setCurrentCoachText(ev.reply ?? "");
          if (ev.phase === "active" && onCommitted) {
            generatePlan().finally(() => onCommitted());
          } else if (ev.refresh_plan && onCommitted) {
            // Mental health agent rebuilt tomorrow's plan — refresh the plan view
            setTimeout(() => onCommitted?.(), 1200);
          }
        } else if (ev.type === "error") {
          setError("Something went wrong. Try again.");
          setCurrentCoachText(FALLBACK_GREETING);
        }
      });
    } catch (e) {
      if (e instanceof AuthError) { onAuthError(); return; }
      setError("Something went wrong. Try again.");
      setCurrentCoachText(FALLBACK_GREETING);
    } finally {
      setLoading(false);
      onLoadingChange(false);
    }
  }

  return (
    <div
      className="shrink-0 flex flex-col"
      style={{ minHeight: "168px", maxHeight: "256px", background: "#faf9ff" }}
    >
      {/* Thin purple rule */}
      <div className="h-px mx-6" style={{ background: "linear-gradient(90deg, #7c3aed22 0%, #a78bfa55 50%, #7c3aed22 100%)" }} />

      {/* Agent status */}
      <div className="flex items-center gap-2 px-6 pt-3 pb-0 shrink-0">
        <span className={`w-1.5 h-1.5 rounded-full ${loading ? "bg-violet-400 animate-pulse" : "bg-violet-500"}`} />
        <span className="text-[10px] font-semibold text-violet-400 uppercase tracking-[0.12em]">
          {loading ? "thinking…" : agentLabel}
        </span>
        {userEcho && !loading && (
          <span className="ml-auto text-[11px] text-slate-400 max-w-[44%] truncate italic">
            {userEcho}
          </span>
        )}
      </div>

      {/* Coach text */}
      <div className="flex-1 overflow-y-auto px-6 py-2">
        <p className="text-[15px] text-slate-800 leading-[1.85] font-normal tracking-[-0.01em]">
          {displayed}
          {(loading || !done) && (
            <span className="inline-block w-[2px] h-[1.05em] bg-violet-400 ml-0.5 align-middle animate-pulse" />
          )}
        </p>
        {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
        {done && chips.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {chips.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="px-3.5 py-1 rounded-full text-xs font-medium text-violet-600 transition-all duration-150"
                style={{ background: "#ede9fe", border: "none" }}
                onMouseEnter={e => { (e.target as HTMLElement).style.background = "#7c3aed"; (e.target as HTMLElement).style.color = "#fff"; }}
                onMouseLeave={e => { (e.target as HTMLElement).style.background = "#ede9fe"; (e.target as HTMLElement).style.color = "#7c3aed"; }}
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Input — borderless style */}
      <div className="shrink-0 px-6 pb-4 pt-1">
        <div className="flex items-center gap-3 rounded-2xl px-4 py-2.5" style={{ background: "#ede9fe40", boxShadow: "inset 0 0 0 1px #7c3aed18" }}>
          <textarea
            ref={inputRef}
            rows={1}
            placeholder="Reply to your coach…"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 80)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
            }}
            className="flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder-violet-300 focus:outline-none overflow-hidden leading-relaxed"
            style={{ minHeight: "22px", border: "none" }}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="shrink-0 w-7 h-7 rounded-xl flex items-center justify-center transition-all disabled:opacity-25"
            style={{ background: "#7c3aed" }}
          >
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
