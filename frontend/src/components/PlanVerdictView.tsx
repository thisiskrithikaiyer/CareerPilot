"use client";

import { useState } from "react";
import { GoalPlan, AgentEvent, commitPlan, generatePlan } from "@/lib/api";

const MODE_META: Record<string, { color: string; bg: string; label: string }> = {
  CRISIS:    { color: "#dc2626", bg: "#fef2f2", label: "CRISIS" },
  URGENT:    { color: "#d97706", bg: "#fffbeb", label: "URGENT" },
  STANDARD:  { color: "#7c3aed", bg: "#f5f3ff", label: "STANDARD" },
  STRATEGIC: { color: "#0284c7", bg: "#f0f9ff", label: "STRATEGIC" },
};

interface Props {
  plan: GoalPlan;
  onCommit: () => void;
  onAgentEvents: (evs: AgentEvent[]) => void;
}

export default function PlanVerdictView({ plan, onCommit, onAgentEvents }: Props) {
  const [committing, setCommitting] = useState(false);

  const s = plan.goal_stratergy;
  const mode = (s.mode ?? "STANDARD").toUpperCase();
  const meta = MODE_META[mode] ?? MODE_META.STANDARD;

  const dailyItems = [
    { label: "job applications", value: s.daily_targets.applications },
    { label: "networking messages", value: s.daily_targets.networking_messages },
    { label: "LinkedIn connects", value: s.daily_targets.linkedin_connects },
    { label: `LeetCode problems (${s.leetcode_tier ?? "standard"})`, value: s.daily_targets.leetcode_problems },
  ];

  async function handleCommit() {
    setCommitting(true);
    onAgentEvents([{
      agent: "goal_planner",
      display_name: "Goal Strategist",
      reason: "Locking in your 10-day plan",
      timestamp: new Date().toISOString(),
    }]);
    await commitPlan();
    onAgentEvents([{
      agent: "daily_check",
      display_name: "Daily Planner",
      reason: "Building today's schedule",
      timestamp: new Date().toISOString(),
    }]);
    await generatePlan();
    onCommit();
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fafafa] px-4 py-10">
      <div className="w-full max-w-md">

        {/* Header */}
        <div className="flex items-center gap-2.5 mb-8">
          <div className="w-7 h-7 rounded-lg bg-violet-700 flex items-center justify-center shrink-0">
            <span className="text-white text-[10px] font-bold tracking-tight">CC</span>
          </div>
          <span className="text-sm font-semibold text-gray-800 tracking-tight">CrisisCoach AI</span>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 tracking-tight mb-1">
          Here&apos;s your 10-day plan
        </h1>
        <p className="text-sm text-slate-400 mb-6">Review it, then commit. We revisit on Day 10.</p>

        {/* Mode + reasoning */}
        <div
          className="rounded-2xl px-4 py-4 mb-5"
          style={{ background: meta.bg, border: `1px solid ${meta.color}22` }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span
              className="text-[11px] font-bold px-2.5 py-0.5 rounded-full"
              style={{ color: meta.color, background: `${meta.color}18` }}
            >
              {meta.label}
            </span>
          </div>
          {s.reasoning && (
            <p className="text-sm text-slate-700 leading-relaxed">{s.reasoning}</p>
          )}
        </div>

        {/* Daily targets */}
        <div className="rounded-2xl overflow-hidden mb-4" style={{ border: "1px solid #ede9fe" }}>
          <div className="px-4 pt-3.5 pb-2">
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.12em]">
              Daily targets
            </p>
          </div>
          <ul className="px-4 pb-4 space-y-2.5">
            {dailyItems.map((item, i) => (
              <li
                key={i}
                className="flex items-center gap-3"
                style={{ animation: `fadeSlideIn 0.3s ease both`, animationDelay: `${i * 80}ms` }}
              >
                <span
                  className="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: "#ede9fe" }}
                >
                  <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <span className="text-sm text-slate-700">
                  <span className="font-bold text-slate-900">{item.value}</span> {item.label}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Role targets */}
        {(s.role_targets.stretch || s.role_targets.realistic || s.role_targets.safety) && (
          <div className="rounded-2xl overflow-hidden mb-4" style={{ border: "1px solid #ede9fe" }}>
            <div className="px-4 pt-3.5 pb-2">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.12em]">Role targets</p>
            </div>
            <ul className="px-4 pb-4 space-y-2">
              {[
                { tag: "Stretch",   val: s.role_targets.stretch,   color: "#dc2626" },
                { tag: "Realistic", val: s.role_targets.realistic, color: "#7c3aed" },
                { tag: "Safety",    val: s.role_targets.safety,    color: "#059669" },
              ].filter(r => r.val).map((r, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0"
                    style={{ color: r.color, background: `${r.color}14` }}
                  >
                    {r.tag}
                  </span>
                  <span className="text-slate-700">{r.val}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Weekly milestones */}
        {s.weekly_milestones?.length > 0 && (
          <div className="rounded-2xl overflow-hidden mb-4" style={{ border: "1px solid #ede9fe" }}>
            <div className="px-4 pt-3.5 pb-2">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.12em]">Milestones</p>
            </div>
            <ul className="px-4 pb-4 space-y-3">
              {s.weekly_milestones.map((m, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span
                    className="text-[10px] font-bold shrink-0 mt-0.5 px-2 py-0.5 rounded-full"
                    style={{ background: "#ede9fe", color: "#7c3aed" }}
                  >
                    Wk {m.week}
                  </span>
                  <span className="text-slate-600 leading-relaxed">{m.goal}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Soft suggestion */}
        {s.suggested_info && (
          <p className="text-xs text-slate-400 leading-relaxed mb-5 px-1">
            💡 {s.suggested_info}
          </p>
        )}

        {/* Commit button */}
        <button
          onClick={handleCommit}
          disabled={committing}
          className="w-full py-3.5 rounded-2xl text-white font-semibold text-sm transition-opacity disabled:opacity-50"
          style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
        >
          {committing ? "Locking in your plan…" : "Looks good — commit this plan →"}
        </button>
      </div>

      <style jsx>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
