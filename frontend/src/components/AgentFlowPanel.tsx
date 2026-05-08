"use client";

import { AgentEvent } from "@/lib/api";

const AGENT_STYLE: Record<string, { dot: string; icon: string; label: string }> = {
  intake:         { dot: "#818cf8", icon: "🎙", label: "Intake"         },
  goal_planner:   { dot: "#7c3aed", icon: "🎯", label: "Goal Planner"   },
  checkin:        { dot: "#059669", icon: "📋", label: "Check-in"       },
  accountability: { dot: "#d97706", icon: "⚖️", label: "Accountability" },
  mental_health:  { dot: "#e11d48", icon: "💙", label: "Wellness"       },
  chat:           { dot: "#94a3b8", icon: "💬", label: "Coach"          },
};

function getStyle(agent: string) {
  return AGENT_STYLE[agent] ?? AGENT_STYLE.chat;
}

function formatTime(iso: string) {
  try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
  catch { return ""; }
}

interface Props {
  events: AgentEvent[];
  isLoading?: boolean;
}

export default function AgentFlowPanel({ events, isLoading }: Props) {
  const latest = events[events.length - 1];

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: "#0b0a12", borderLeft: "1px solid #1a1630" }}>

      {/* Header */}
      <div className="px-4 pt-4 pb-3 shrink-0">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em]" style={{ color: "#6d5f9e" }}>Agent Activity</p>
          <span className={`w-1.5 h-1.5 rounded-full ${isLoading ? "animate-pulse" : ""}`} style={{ background: isLoading ? "#a78bfa" : "#3b2d6a" }} />
        </div>
        <p className="text-[10px] mt-0.5" style={{ color: "#3d3558" }}>LangGraph routing</p>
      </div>

      {/* Active agent */}
      {latest ? (
        <div className="mx-3 mb-3 rounded-xl px-3 py-2.5 shrink-0" style={{ background: "#120f1f", border: "1px solid #1f1a38" }}>
          <p className="text-[9px] font-semibold uppercase tracking-[0.1em] mb-1" style={{ color: "#6d5f9e" }}>Active</p>
          <div className="flex items-center gap-2">
            <span className="text-sm">{getStyle(latest.agent).icon}</span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate" style={{ color: "#c4b5fd" }}>{latest.display_name}</p>
              <p className="text-[10px] truncate font-mono" style={{ color: "#4a3f72" }}>{latest.agent}</p>
            </div>
            {isLoading && (
              <span className="text-[9px] animate-pulse shrink-0" style={{ color: "#7c3aed" }}>running…</span>
            )}
          </div>
        </div>
      ) : (
        <div className="mx-3 mb-3 shrink-0">
          <p className="text-[11px] italic" style={{ color: "#2e2650" }}>Waiting for first message…</p>
        </div>
      )}

      {/* Event log */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-0">
        {events.length === 0 ? (
          <p className="text-[11px] text-center mt-4" style={{ color: "#2e2650" }}>No events yet</p>
        ) : (
          events.map((ev, i) => {
            const style = getStyle(ev.agent);
            const isLast = i === events.length - 1;
            return (
              <div key={i} className="flex gap-2.5">
                <div className="flex flex-col items-center">
                  <div
                    className="w-2 h-2 rounded-full shrink-0 mt-1"
                    style={{ background: style.dot, opacity: isLast ? 0.9 : 0.25 }}
                  />
                  {!isLast && <div className="w-px flex-1 my-1" style={{ background: "#1a1630" }} />}
                </div>
                <div className="pb-3 min-w-0">
                  <div className="flex items-baseline gap-1.5 flex-wrap">
                    <span className="text-xs font-medium" style={{ color: isLast ? "#a78bfa" : "#4a3f72" }}>{ev.display_name}</span>
                    <span className="text-[10px]" style={{ color: "#2e2650" }}>{formatTime(ev.timestamp)}</span>
                  </div>
                  <p className="text-[11px] mt-0.5 leading-relaxed" style={{ color: isLast ? "#6d5f9e" : "#3a3260" }}>{ev.reason}</p>
                </div>
              </div>
            );
          })
        )}

        {isLoading && (
          <div className="flex gap-2.5">
            <div className="flex flex-col items-center">
              <div className="w-2 h-2 rounded-full shrink-0 mt-1 animate-pulse" style={{ background: "#7c3aed" }} />
            </div>
            <p className="text-[11px] animate-pulse pb-3" style={{ color: "#5b4a8a" }}>Supervisor routing…</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 shrink-0" style={{ borderTop: "1px solid #1a1630" }}>
        <p className="text-[10px]" style={{ color: "#2e2650" }}>{events.length} event{events.length !== 1 ? "s" : ""}</p>
      </div>
    </div>
  );
}
