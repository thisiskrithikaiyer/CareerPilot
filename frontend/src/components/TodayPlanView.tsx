"use client";

import { useState, useEffect } from "react";
import { fetchTodayPlan, generatePlan, submitDailyLog, updateTaskStatus, TodayPlan, DailyLogData } from "@/lib/api";

const PRIORITY_COLOR: Record<string, { text: string; bg: string }> = {
  urgent:   { text: "#dc2626", bg: "#fef2f2" },
  standard: { text: "#7c3aed", bg: "#f5f3ff" },
  recovery: { text: "#0284c7", bg: "#f0f9ff" },
};

const BLOCK_META = {
  morning: { emoji: "🌅", label: "Morning" },
  midday:  { emoji: "☀️",  label: "Midday"  },
  evening: { emoji: "🌙", label: "Evening" },
};

const EMPTY_LOG: DailyLogData = {
  dsa_problems: 0,
  other_prep: "",
  system_design_topic: "",
  applications_sent: 0,
  networking_sent: 0,
  coffee_chat: 0,
  called_for_calls: 0,
  oa_pending: 0,
  recruiter_screens: 0,
  technical_rounds: 0,
  final_rounds: 0,
  mocks_done: 0,
  notes: "",
};

interface Props {
  sessionDate: string;
  onAdvanceDay: () => Promise<void>;
}

export default function TodayPlanView({ sessionDate, onAdvanceDay }: Props) {
  const [plan, setPlan] = useState<TodayPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [log, setLog] = useState<DailyLogData>(EMPTY_LOG);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [todayDone, setTodayDone] = useState(false);
  const [advancing, setAdvancing] = useState(false);

  useEffect(() => {
    setLoading(true);
    setPlan(null);
    setChecked(new Set());
    setLog(EMPTY_LOG);
    setSaved(false);
    setTodayDone(false);
    fetchTodayPlan(sessionDate).then((p) => {
      setPlan(p);
      // Restore persisted completion state — checkboxes survive reloads and
      // reflect tasks closed from chat ("close the leetcode task").
      const status = p?.task_status ?? {};
      setChecked(new Set(Object.keys(status).filter((k) => status[k])));
      setLoading(false);
    });
  }, [sessionDate]);

  async function handleGenerate() {
    setGenerating(true);
    const p = await generatePlan();
    setPlan(p);
    setChecked(new Set());
    setGenerating(false);
  }

  function toggleTask(key: string) {
    const willComplete = !checked.has(key);
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
    // Persist so the next-day planner knows what was actually completed.
    updateTaskStatus(key, willComplete, sessionDate);
  }

  function setLogField<K extends keyof DailyLogData>(key: K, value: DailyLogData[K]) {
    setLog((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSaveLog() {
    setSaving(true);
    try {
      await submitDailyLog({ ...log, date: sessionDate });
      setSaved(true);
      setTimeout(() => setTodayDone(true), 600);
    } finally {
      setSaving(false);
    }
  }

  async function handleStartTomorrow() {
    setAdvancing(true);
    try {
      await onAdvanceDay();
    } finally {
      setAdvancing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-6 h-6 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin mb-3" />
        <p className="text-xs text-slate-400">Loading today&apos;s plan…</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center mb-4" style={{ background: "#f5f3ff" }}>
          <span className="text-xl">📋</span>
        </div>
        <p className="text-sm font-semibold text-slate-800 mb-1">No plan for today yet</p>
        <p className="text-xs text-slate-400 max-w-xs leading-relaxed mb-5">
          Generate your personalized daily plan based on your goals and current progress.
        </p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-5 py-2 text-white text-sm font-semibold rounded-xl transition-opacity disabled:opacity-50"
          style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
        >
          {generating ? "Building your plan…" : "Generate today's plan"}
        </button>
      </div>
    );
  }

  const mode = plan.priority_mode?.toLowerCase() ?? "standard";
  const modeColor = PRIORITY_COLOR[mode] ?? PRIORITY_COLOR.standard;

  return (
    <div className="space-y-5 pb-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-base font-bold text-slate-900">Today&apos;s Plan</p>
          <p className="text-xs text-slate-400 mt-0.5">{plan.date}</p>
        </div>
        <div className="flex items-center gap-2.5">
          <span
            className="text-xs font-bold px-3 py-1 rounded-full"
            style={{ color: modeColor.text, background: modeColor.bg }}
          >
            {plan.priority_mode?.toUpperCase()}
          </span>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="text-xs font-medium disabled:opacity-40 transition-colors"
            style={{ color: "#7c3aed" }}
          >
            {generating ? "Rebuilding…" : "↻ Rebuild"}
          </button>
        </div>
      </div>

      {/* Coach note */}
      {plan.coach_note && (
        <div className="rounded-2xl px-4 py-3.5" style={{ background: "#faf9ff" }}>
          <p className="text-sm text-slate-700 leading-relaxed">{plan.coach_note}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl p-4 text-center" style={{ background: "#f8fafc" }}>
          <p className="text-2xl font-bold" style={{ color: "#7c3aed" }}>{plan.job_apps}</p>
          <p className="text-xs text-slate-400 mt-0.5">Job apps today</p>
        </div>
        <div className="rounded-2xl p-4 text-center" style={{ background: "#f8fafc" }}>
          <p className="text-2xl font-bold" style={{ color: "#7c3aed" }}>{plan.leetcode_problems}</p>
          <p className="text-xs text-slate-400 mt-0.5">{plan.leetcode_topic || "LeetCode"}</p>
        </div>
      </div>

      {/* Schedule with checkboxes */}
      {plan.schedule && (
        <div className="space-y-3">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.12em]">Schedule</p>
          {(["morning", "midday", "evening"] as const).map((key, blockIdx) => {
            const block = plan.schedule[key];
            if (!block?.tasks?.length) return null;
            const meta = BLOCK_META[key];
            return (
              <div
                key={key}
                className="rounded-2xl overflow-hidden"
                style={{
                  background: "#f8fafc",
                  animation: "blockIn 0.35s ease both",
                  animationDelay: `${blockIdx * 120}ms`,
                }}
              >
                <div className="flex items-center gap-2 px-4 py-2.5">
                  <span className="text-sm">{meta.emoji}</span>
                  <p className="text-xs font-semibold text-slate-600">{block.time || meta.label}</p>
                </div>
                <ul className="px-4 pb-3.5 space-y-2.5">
                  {block.tasks.map((task, i) => {
                    const taskKey = `${key}-${i}`;
                    const done = checked.has(taskKey);
                    return (
                      <li
                        key={i}
                        className="flex items-start gap-3 cursor-pointer group"
                        style={{
                          animation: "taskIn 0.3s ease both",
                          animationDelay: `${blockIdx * 120 + i * 70 + 80}ms`,
                        }}
                        onClick={() => toggleTask(taskKey)}
                      >
                        <span
                          className="mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 leading-none border transition-all"
                          style={
                            done
                              ? { background: "#7c3aed", borderColor: "#7c3aed" }
                              : { background: "#fff", borderColor: "#ddd6fe" }
                          }
                        >
                          {done && (
                            <svg width="8" height="7" viewBox="0 0 8 7" fill="none">
                              <path d="M1 3.5L3 5.5L7 1.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </span>
                        <span
                          className="text-xs text-slate-600 leading-relaxed transition-all"
                          style={done ? { textDecoration: "line-through", color: "#94a3b8" } : {}}
                        >
                          {task}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      {/* Daily Log / Done card */}
      {todayDone ? (
        <div className="done-card rounded-3xl overflow-hidden relative" style={{ border: "1px solid #ede9fe", background: "linear-gradient(160deg, #faf9ff 0%, #f5f3ff 100%)" }}>
          <span className="orb orb-1" />
          <span className="orb orb-2" />
          <span className="orb orb-3" />

          <div className="relative flex flex-col items-center text-center px-8 py-10 z-10">
            <div className="check-pop w-14 h-14 rounded-full flex items-center justify-center mb-5 shadow-lg" style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}>
              <svg width="26" height="22" viewBox="0 0 26 22" fill="none">
                <path d="M2 11L9.5 18.5L24 3" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>

            <p className="text-lg font-bold text-slate-900 mb-1">Today is done.</p>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">
              Great work — your progress has been saved.<br />
              Ready for tomorrow?
            </p>

            {/* Summary pills */}
            <div className="flex flex-wrap justify-center gap-2 mb-7">
              {[
                { label: "DSA", val: log.dsa_problems },
                { label: "Apps", val: log.applications_sent },
                { label: "Networking", val: log.networking_sent },
                { label: "Coffee chats", val: log.coffee_chat },
                { label: "Mocks", val: log.mocks_done },
              ].filter((s) => (s.val ?? 0) > 0).map((s) => (
                <span
                  key={s.label}
                  className="text-xs font-semibold px-3 py-1 rounded-full"
                  style={{ background: "#ede9fe", color: "#7c3aed" }}
                >
                  {s.val} {s.label}
                </span>
              ))}
            </div>

            {/* Start Tomorrow */}
            <button
              onClick={handleStartTomorrow}
              disabled={advancing}
              className="px-6 py-2.5 text-white text-sm font-semibold rounded-2xl shadow-md transition-all disabled:opacity-50 mb-3"
              style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
            >
              {advancing ? "Building tomorrow's plan…" : "Start Tomorrow →"}
            </button>

            <button
              onClick={() => setTodayDone(false)}
              className="text-xs text-slate-400 hover:text-violet-500 transition-colors underline underline-offset-2"
            >
              Edit log
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid #ede9fe" }}>
          <div className="px-4 py-3" style={{ background: "#f5f3ff" }}>
            <p className="text-xs font-semibold text-violet-700 uppercase tracking-[0.1em]">Daily Log</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Track what you actually did today — saved notes inform tomorrow&apos;s plan.</p>
          </div>
          <div className="px-4 py-4 space-y-4" style={{ background: "#fff" }}>
            <div className="grid grid-cols-3 gap-3">
              {([
                ["dsa_problems",     "DSA Problems"],
                ["applications_sent","Apps Sent"],
                ["networking_sent",  "Networking"],
                ["coffee_chat",      "Coffee Chats"],
                ["called_for_calls", "Calls Received"],
                ["oa_pending",       "OA Pending"],
                ["recruiter_screens","Recruiter Screens"],
                ["technical_rounds", "Tech Rounds"],
                ["final_rounds",     "Final Rounds"],
                ["mocks_done",       "Mocks Done"],
              ] as [keyof DailyLogData, string][]).map(([field, label]) => (
                <div key={field}>
                  <label className="text-[10px] text-slate-400 block mb-1">{label}</label>
                  <input
                    type="number"
                    min={0}
                    value={(log[field] as number) ?? 0}
                    onChange={(e) => setLogField(field, parseInt(e.target.value) || 0)}
                    className="w-full text-sm font-semibold text-slate-800 rounded-lg px-2.5 py-1.5 text-center outline-none"
                    style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
                  />
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Other Prep</label>
                <input
                  type="text"
                  placeholder="e.g. behavioral prep, resume"
                  value={log.other_prep ?? ""}
                  onChange={(e) => setLogField("other_prep", e.target.value)}
                  className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-1.5 outline-none"
                  style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">System Design Topic</label>
                <input
                  type="text"
                  placeholder="e.g. rate limiter, URL shortener"
                  value={log.system_design_topic ?? ""}
                  onChange={(e) => setLogField("system_design_topic", e.target.value)}
                  className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-1.5 outline-none"
                  style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">Notes</label>
              <textarea
                rows={3}
                placeholder="How did today go? Any blockers, wins, or things to focus on tomorrow?"
                value={log.notes ?? ""}
                onChange={(e) => setLogField("notes", e.target.value)}
                className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none resize-none"
                style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
              />
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleSaveLog}
                disabled={saving}
                className="px-5 py-2 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
                style={{
                  background: saved ? "#16a34a" : "linear-gradient(135deg, #7c3aed, #a78bfa)",
                }}
              >
                {saving ? "Saving…" : saved ? "Saved!" : "Save daily log"}
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes blockIn {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes taskIn {
          from { opacity: 0; transform: translateX(-6px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes doneIn {
          from { opacity: 0; transform: translateY(16px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes checkPop {
          0%   { transform: scale(0) rotate(-10deg); }
          60%  { transform: scale(1.15) rotate(3deg); }
          100% { transform: scale(1) rotate(0deg); }
        }
        @keyframes orbFloat {
          0%, 100% { transform: translateY(0) scale(1); opacity: 0.18; }
          50%       { transform: translateY(-12px) scale(1.08); opacity: 0.28; }
        }
        .done-card {
          animation: doneIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .check-pop {
          animation: checkPop 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.15s both;
        }
        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(28px);
          pointer-events: none;
        }
        .orb-1 {
          width: 120px; height: 120px;
          background: #a78bfa;
          top: -30px; right: -20px;
          animation: orbFloat 5s ease-in-out infinite;
        }
        .orb-2 {
          width: 80px; height: 80px;
          background: #7c3aed;
          bottom: 10px; left: -10px;
          animation: orbFloat 7s ease-in-out 1s infinite;
        }
        .orb-3 {
          width: 60px; height: 60px;
          background: #c4b5fd;
          bottom: 30px; right: 40px;
          animation: orbFloat 6s ease-in-out 2.5s infinite;
        }
      `}</style>
    </div>
  );
}
