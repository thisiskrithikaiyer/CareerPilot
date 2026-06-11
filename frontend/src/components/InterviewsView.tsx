"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchInterviews,
  createInterview,
  updateInterview,
  InterviewEntry,
  InterviewStage,
  InterviewContact,
  InterviewStatus,
} from "@/lib/api";

const STAGES: { value: InterviewStage; label: string }[] = [
  { value: "phone_screen", label: "Phone Screen" },
  { value: "technical", label: "Technical" },
  { value: "system_design", label: "System Design" },
  { value: "behavioral", label: "Behavioral" },
  { value: "onsite", label: "Onsite" },
  { value: "final", label: "Final" },
];

const CONTACTS: { value: InterviewContact; label: string }[] = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "referral", label: "Referral" },
  { value: "job_board", label: "Job Board" },
  { value: "cold_apply", label: "Cold Apply" },
  { value: "recruiter", label: "Recruiter" },
  { value: "other", label: "Other" },
];

const STATUS_STYLE: Record<InterviewStatus, { label: string; color: string; bg: string }> = {
  pending: { label: "Pending", color: "#d97706", bg: "#fffbeb" },
  pass:    { label: "Passed",  color: "#16a34a", bg: "#f0fdf4" },
  fail:    { label: "Failed",  color: "#dc2626", bg: "#fef2f2" },
};

function stageLabel(stage: string) {
  return STAGES.find((s) => s.value === stage)?.label ?? stage;
}

function formatDate(d: string) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

const inputStyle = { background: "#f8fafc", border: "1px solid #e2e8f0" };

interface AddFormProps {
  sessionDate: string;
  onSaved: (row: InterviewEntry) => void;
  onCancel: () => void;
}

function AddInterviewForm({ sessionDate, onSaved, onCancel }: AddFormProps) {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [stage, setStage] = useState<InterviewStage>("phone_screen");
  const [date, setDate] = useState(sessionDate);
  const [contact, setContact] = useState<InterviewContact>("job_board");
  const [topics, setTopics] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!company.trim()) { setError("Company is required."); return; }
    setSaving(true);
    setError(null);
    try {
      const row = await createInterview({
        company: company.trim(),
        role: role.trim() || undefined,
        stage,
        date,
        how_contacted: contact,
        topics: topics.split(",").map((t) => t.trim()).filter(Boolean),
        notes: notes.trim() || undefined,
        status: "pending",
      });
      onSaved(row);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save interview.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid #ede9fe", animation: "rowIn 0.3s ease both" }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ background: "#f5f3ff" }}>
        <p className="text-xs font-semibold text-violet-700 uppercase tracking-[0.1em]">Log an Interview</p>
        <button onClick={onCancel} className="text-xs text-slate-400 hover:text-slate-600 transition-colors">Cancel</button>
      </div>
      <div className="px-4 py-4 space-y-3 bg-white">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Company *</label>
            <input
              type="text" value={company} onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Stripe" autoFocus
              className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none" style={inputStyle}
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Role</label>
            <input
              type="text" value={role} onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. ML Engineer"
              className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none" style={inputStyle}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Stage</label>
            <select
              value={stage} onChange={(e) => setStage(e.target.value as InterviewStage)}
              className="w-full text-xs text-slate-700 rounded-lg px-2 py-2 outline-none" style={inputStyle}
            >
              {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Date</label>
            <input
              type="date" value={date} onChange={(e) => setDate(e.target.value)}
              className="w-full text-xs text-slate-700 rounded-lg px-2 py-1.5 outline-none" style={inputStyle}
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Source</label>
            <select
              value={contact} onChange={(e) => setContact(e.target.value as InterviewContact)}
              className="w-full text-xs text-slate-700 rounded-lg px-2 py-2 outline-none" style={inputStyle}
            >
              {CONTACTS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="text-[10px] text-slate-400 block mb-1">Topics (comma-separated)</label>
          <input
            type="text" value={topics} onChange={(e) => setTopics(e.target.value)}
            placeholder="e.g. dynamic programming, system design"
            className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none" style={inputStyle}
          />
        </div>

        <div>
          <label className="text-[10px] text-slate-400 block mb-1">Notes</label>
          <textarea
            rows={2} value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Recruiter said 2 rounds, focus on ML systems"
            className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none resize-none" style={inputStyle}
          />
        </div>

        {error && <p className="text-xs text-rose-500">{error}</p>}

        <div className="flex justify-end">
          <button
            onClick={handleSave} disabled={saving}
            className="px-5 py-2 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
          >
            {saving ? "Saving…" : "Save interview"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface CardProps {
  row: InterviewEntry;
  upcoming: boolean;
  onUpdated: (id: string, patch: Partial<InterviewEntry>) => void;
}

function InterviewCard({ row, upcoming, onUpdated }: CardProps) {
  const [postMortem, setPostMortem] = useState(false);
  const [wentWrong, setWentWrong] = useState(row.what_went_wrong ?? "");
  const [saving, setSaving] = useState(false);
  const status = STATUS_STYLE[row.status] ?? STATUS_STYLE.pending;

  async function setStatus(next: InterviewStatus) {
    if (next === "fail") { setPostMortem(true); return; }
    setSaving(true);
    try {
      await updateInterview(row.id, { status: next });
      onUpdated(row.id, { status: next });
    } finally {
      setSaving(false);
    }
  }

  async function saveFail() {
    setSaving(true);
    try {
      await updateInterview(row.id, { status: "fail", what_went_wrong: wentWrong.trim() || undefined });
      onUpdated(row.id, { status: "fail", what_went_wrong: wentWrong.trim() || null });
      setPostMortem(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl px-4 py-3.5 bg-white" style={{ border: "1px solid #ede9fe", animation: "rowIn 0.3s ease both" }}>
      <div className="flex items-start gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-sm font-bold"
          style={{ background: "#f5f3ff", color: "#7c3aed" }}
        >
          {row.company.slice(0, 1).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-slate-800">{row.company}</p>
            {row.role && <p className="text-xs text-slate-400">· {row.role}</p>}
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full ml-auto" style={{ color: status.color, background: status.bg }}>
              {status.label.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full" style={{ background: "#ede9fe", color: "#7c3aed" }}>
              {stageLabel(row.stage)}
            </span>
            <span className="text-[11px] text-slate-400">{formatDate(row.date)}</span>
            {row.how_contacted && (
              <span className="text-[11px] text-slate-400 capitalize">via {row.how_contacted.replace("_", " ")}</span>
            )}
          </div>
          {(row.topics?.length ?? 0) > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {row.topics!.map((t) => (
                <span key={t} className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "#f8fafc", border: "1px solid #e2e8f0", color: "#64748b" }}>
                  {t}
                </span>
              ))}
            </div>
          )}
          {row.notes && <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">{row.notes}</p>}
          {row.status === "fail" && row.what_went_wrong && !postMortem && (
            <p className="text-[11px] mt-2 px-2.5 py-1.5 rounded-lg leading-relaxed" style={{ background: "#fef2f2", color: "#b91c1c" }}>
              <span className="font-semibold">What went wrong:</span> {row.what_went_wrong}
            </p>
          )}

          {/* Outcome controls for non-upcoming pending interviews */}
          {!upcoming && row.status === "pending" && !postMortem && (
            <div className="flex items-center gap-2 mt-2.5">
              <p className="text-[10px] text-slate-400 mr-1">Outcome:</p>
              <button
                onClick={() => setStatus("pass")} disabled={saving}
                className="text-[11px] font-semibold px-3 py-1 rounded-full transition-all disabled:opacity-50"
                style={{ background: "#f0fdf4", color: "#16a34a", border: "1px solid #bbf7d0" }}
              >
                ✓ Passed
              </button>
              <button
                onClick={() => setStatus("fail")} disabled={saving}
                className="text-[11px] font-semibold px-3 py-1 rounded-full transition-all disabled:opacity-50"
                style={{ background: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca" }}
              >
                ✗ Failed
              </button>
            </div>
          )}

          {postMortem && (
            <div className="mt-2.5 space-y-2">
              <textarea
                rows={2} value={wentWrong} onChange={(e) => setWentWrong(e.target.value)}
                placeholder="What went wrong? e.g. Froze on the DP follow-up" autoFocus
                className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none resize-none"
                style={{ background: "#fef2f2", border: "1px solid #fecaca" }}
              />
              <div className="flex gap-2 justify-end">
                <button onClick={() => setPostMortem(false)} className="text-[11px] text-slate-400 hover:text-slate-600 px-2">Cancel</button>
                <button
                  onClick={saveFail} disabled={saving}
                  className="text-[11px] font-semibold px-3 py-1 rounded-full text-white transition-all disabled:opacity-50"
                  style={{ background: "#dc2626" }}
                >
                  {saving ? "Saving…" : "Save outcome"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface Props {
  sessionDate: string;
}

export default function InterviewsView({ sessionDate }: Props) {
  const [rows, setRows] = useState<InterviewEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    fetchInterviews().then((data) => {
      setRows(data);
      setLoading(false);
    });
  }, []);

  useEffect(load, [load]);

  function handleUpdated(id: string, patch: Partial<InterviewEntry>) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  const upcoming = rows.filter((r) => r.date >= sessionDate).sort((a, b) => a.date.localeCompare(b.date));
  const past = rows.filter((r) => r.date < sessionDate);
  const passed = past.filter((r) => r.status === "pass").length;
  const failed = past.filter((r) => r.status === "fail").length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-6 h-6 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin mb-3" />
        <p className="text-xs text-slate-400">Loading interviews…</p>
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-base font-bold text-slate-900">Interviews</p>
          <p className="text-xs text-slate-400 mt-0.5">
            Logging interviews re-scores your skill map and tunes your plan.
          </p>
        </div>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="px-4 py-2 text-white text-xs font-semibold rounded-xl transition-all"
            style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
          >
            + Log interview
          </button>
        )}
      </div>

      {/* Funnel stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Upcoming", val: upcoming.length, color: "#7c3aed" },
          { label: "Completed", val: past.length, color: "#475569" },
          { label: "Passed", val: passed, color: "#16a34a" },
          { label: "Failed", val: failed, color: "#dc2626" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl p-3.5 text-center" style={{ background: "#f8fafc" }}>
            <p className="text-xl font-bold" style={{ color: s.color }}>{s.val}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {adding && (
        <AddInterviewForm
          sessionDate={sessionDate}
          onCancel={() => setAdding(false)}
          onSaved={(row) => {
            setRows((prev) => [row, ...prev]);
            setAdding(false);
          }}
        />
      )}

      {rows.length === 0 && !adding && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center mb-4" style={{ background: "#f5f3ff" }}>
            <span className="text-xl">🎤</span>
          </div>
          <p className="text-sm font-semibold text-slate-800 mb-1">No interviews logged yet</p>
          <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
            Log every screen and round — your coach spots patterns across them and adjusts your prep.
          </p>
        </div>
      )}

      {upcoming.length > 0 && (
        <div className="space-y-2.5">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.12em]">Upcoming</p>
          {upcoming.map((row) => (
            <InterviewCard key={row.id} row={row} upcoming onUpdated={handleUpdated} />
          ))}
        </div>
      )}

      {past.length > 0 && (
        <div className="space-y-2.5">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-[0.12em]">Past</p>
          {past.map((row) => (
            <InterviewCard key={row.id} row={row} upcoming={false} onUpdated={handleUpdated} />
          ))}
        </div>
      )}

      <style jsx>{`
        @keyframes rowIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
