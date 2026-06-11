"use client";

import { useState, useEffect } from "react";
import { fetchDashboard, DashboardData, InterviewEntry } from "@/lib/api";

function formatDate(d: string) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function prettySkill(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function scoreColor(score: number) {
  if (score < 0.4) return "#dc2626";
  if (score < 0.7) return "#d97706";
  return "#16a34a";
}

function SectionCard({ title, children, empty }: { title: string; children?: React.ReactNode; empty?: string }) {
  return (
    <div className="rounded-2xl overflow-hidden bg-white" style={{ border: "1px solid #ede9fe" }}>
      <div className="px-4 py-2.5" style={{ background: "#f5f3ff" }}>
        <p className="text-[10px] font-semibold text-violet-700 uppercase tracking-[0.12em]">{title}</p>
      </div>
      <div className="px-4 py-3.5">
        {children ?? <p className="text-xs text-slate-300 italic py-2">{empty}</p>}
      </div>
    </div>
  );
}

function UpcomingRow({ row }: { row: InterviewEntry }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold" style={{ background: "#f5f3ff", color: "#7c3aed" }}>
        {row.company.slice(0, 1).toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-slate-800 truncate">
          {row.company}{row.role ? ` · ${row.role}` : ""}
        </p>
        <p className="text-[11px] text-slate-400 capitalize">{row.stage.replace("_", " ")}</p>
      </div>
      <p className="text-[11px] font-semibold shrink-0" style={{ color: "#7c3aed" }}>{formatDate(row.date)}</p>
    </div>
  );
}

interface Props {
  sessionDate: string;
  refreshKey: number;
  onGoToInterviews: () => void;
}

export default function OverviewView({ sessionDate, refreshKey, onGoToInterviews }: Props) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Keep showing the previous snapshot while a refresh is in flight.
    fetchDashboard().then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [refreshKey, sessionDate]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-6 h-6 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin mb-3" />
        <p className="text-xs text-slate-400">Loading your dashboard…</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <p className="text-sm font-semibold text-slate-800 mb-1">Couldn&apos;t load the dashboard</p>
        <p className="text-xs text-slate-400">Check that the backend is running, then switch tabs to retry.</p>
      </div>
    );
  }

  const snap = data.snapshot ?? {};
  const goal = data.active_goal?.goal_stratergy;
  const targets = goal?.daily_targets;
  const skills = Object.entries(data.skill_map ?? {}).sort((a, b) => a[1].score - b[1].score);
  const checkins = data.recent_checkins ?? [];
  const upcoming = data.upcoming_interviews ?? [];

  // Today's actuals vs goal targets
  const log = data.today_log;
  const targetRows = targets
    ? [
        { label: "Applications", done: log?.applications_sent ?? 0, target: targets.applications ?? 0 },
        { label: "Networking", done: log?.networking_sent ?? 0, target: targets.networking_messages ?? 0 },
        { label: "LeetCode", done: log?.dsa_problems ?? 0, target: targets.leetcode_problems ?? 0 },
      ].filter((r) => r.target > 0)
    : [];

  const heroStats = [
    { label: "Day", val: snap.days_since != null ? `${snap.days_since}` : "—" },
    { label: "Days left", val: snap.days_left != null ? `${snap.days_left}` : "—" },
    { label: "Open tasks", val: snap.open_tasks != null ? `${snap.open_tasks}` : "—" },
    { label: "Mood", val: snap.mood_score != null ? `${snap.mood_score}/10` : "—" },
    { label: "Energy", val: snap.energy_score != null ? `${snap.energy_score}/10` : "—" },
  ];

  return (
    <div className="space-y-5 pb-6">
      {/* Hero snapshot */}
      <div className="rounded-3xl px-6 py-5 text-white relative overflow-hidden" style={{ background: "linear-gradient(135deg, #6d28d9 0%, #7c3aed 45%, #a78bfa 100%)" }}>
        <div className="relative z-10">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-bold">{snap.role ? `${snap.role} search` : "Your job search"}</p>
            {snap.phase && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide" style={{ background: "rgba(255,255,255,0.18)" }}>
                {snap.phase}
              </span>
            )}
          </div>
          <p className="text-[11px] mt-0.5" style={{ color: "#ddd6fe" }}>
            {formatDate(sessionDate)}
            {snap.leetcode_level ? ` · LeetCode: ${snap.leetcode_level.replace(/_/g, " ")}` : ""}
          </p>
          <div className="flex gap-6 mt-4 flex-wrap">
            {heroStats.map((s) => (
              <div key={s.label}>
                <p className="text-xl font-bold leading-none">{s.val}</p>
                <p className="text-[10px] mt-1" style={{ color: "#c4b5fd" }}>{s.label}</p>
              </div>
            ))}
          </div>
        </div>
        <span className="absolute rounded-full" style={{ width: 180, height: 180, background: "rgba(255,255,255,0.07)", top: -60, right: -40 }} />
        <span className="absolute rounded-full" style={{ width: 100, height: 100, background: "rgba(255,255,255,0.06)", bottom: -30, right: 90 }} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Today vs targets */}
        <SectionCard title="Today vs Targets" empty={targets ? undefined : "Commit a goal plan to set daily targets."}>
          {targetRows.length > 0 ? (
            <div className="space-y-3">
              {targetRows.map((r) => {
                const pct = Math.min(100, Math.round((r.done / r.target) * 100));
                return (
                  <div key={r.label}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-medium text-slate-600">{r.label}</p>
                      <p className="text-[11px] font-semibold" style={{ color: pct >= 100 ? "#16a34a" : "#7c3aed" }}>
                        {r.done}/{r.target}
                      </p>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#f1f5f9" }}>
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${pct}%`, background: pct >= 100 ? "#16a34a" : "linear-gradient(90deg, #7c3aed, #a78bfa)" }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : targets ? (
            <p className="text-xs text-slate-300 italic py-2">No daily targets set yet.</p>
          ) : null}
        </SectionCard>

        {/* Upcoming interviews */}
        <SectionCard title="Upcoming Interviews" empty={upcoming.length === 0 ? "Nothing scheduled — log interviews as they land." : undefined}>
          {upcoming.length > 0 && (
            <div className="divide-y divide-slate-50">
              {upcoming.slice(0, 4).map((row) => <UpcomingRow key={row.id} row={row} />)}
              <button onClick={onGoToInterviews} className="text-[11px] font-semibold pt-2.5 transition-colors" style={{ color: "#7c3aed" }}>
                View all interviews →
              </button>
            </div>
          )}
        </SectionCard>

        {/* Skill map */}
        <SectionCard title="Skill Map" empty={skills.length === 0 ? "Upload your resume or log an interview to build your skill map." : undefined}>
          {skills.length > 0 && (
            <div className="space-y-3">
              {skills.slice(0, 8).map(([skill, info]) => (
                <div key={skill} title={info.evidence?.join(" · ")}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-medium text-slate-600">{prettySkill(skill)}</p>
                    <p className="text-[11px] font-semibold" style={{ color: scoreColor(info.score) }}>
                      {Math.round(info.score * 100)}%
                    </p>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#f1f5f9" }}>
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.round(info.score * 100)}%`, background: scoreColor(info.score) }} />
                  </div>
                  {info.evidence && info.evidence.length > 0 && (
                    <p className="text-[10px] text-slate-400 mt-0.5 truncate">{info.evidence[0]}</p>
                  )}
                </div>
              ))}
              {(data.tracking_skills?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {data.tracking_skills!.map((s) => (
                    <span key={s} className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "#f8fafc", border: "1px solid #e2e8f0", color: "#64748b" }}>
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </SectionCard>

        {/* Mood trend */}
        <SectionCard title="Mood & Energy" empty={checkins.length === 0 ? "Check in each evening to track how you're holding up." : undefined}>
          {checkins.length > 0 && (
            <div>
              <div className="flex items-end gap-1.5 h-16 mb-2">
                {[...checkins].reverse().map((c) => (
                  <div key={c.id} className="flex-1 flex items-end gap-0.5 h-full" title={new Date(c.created_at).toLocaleDateString()}>
                    <div className="flex-1 rounded-t" style={{ height: `${c.mood_score * 10}%`, background: "#7c3aed", opacity: 0.85 }} />
                    <div className="flex-1 rounded-t" style={{ height: `${c.energy_score * 10}%`, background: "#c4b5fd" }} />
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
                  <span className="w-2 h-2 rounded-sm" style={{ background: "#7c3aed" }} /> Mood
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
                  <span className="w-2 h-2 rounded-sm" style={{ background: "#c4b5fd" }} /> Energy
                </span>
                <span className="ml-auto text-[10px] text-slate-300">last {checkins.length} check-ins</span>
              </div>
              {checkins[0]?.blockers && checkins[0].blockers.length > 0 && (
                <p className="text-[11px] mt-3 px-2.5 py-1.5 rounded-lg leading-relaxed" style={{ background: "#fffbeb", color: "#b45309" }}>
                  Latest blocker: {checkins[0].blockers[0]}
                </p>
              )}
            </div>
          )}
        </SectionCard>
      </div>

      {/* Goal milestones */}
      {goal?.weekly_milestones && goal.weekly_milestones.length > 0 && (
        <SectionCard title="Weekly Milestones">
          <div className="space-y-2.5">
            {goal.weekly_milestones.map((m, i) => (
              <div key={i} className="flex items-start gap-3">
                <span
                  className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
                  style={{ background: "#ede9fe", color: "#7c3aed" }}
                >
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-700">{m.week}</p>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{m.goal}</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}
