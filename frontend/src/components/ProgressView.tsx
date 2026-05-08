"use client";

import { useState, useEffect, useRef } from "react";
import { fetchDailyLogs, submitDailyLog, DailyLogEntry, DailyLogData } from "@/lib/api";

const COLUMNS: { key: keyof DailyLogData; label: string; short: string; type: "num" | "text" | "notes" }[] = [
  { key: "dsa_problems",      label: "# DSA Problems (5)", short: "DSA",        type: "num"   },
  { key: "other_prep",        label: "Other Prep",          short: "Other",      type: "text"  },
  { key: "system_design_topic",label:"System Design Topic", short: "Sys Design", type: "text"  },
  { key: "applications_sent", label: "Applications Sent",   short: "Apps",       type: "num"   },
  { key: "networking_sent",   label: "Networking Sent",     short: "Networking", type: "num"   },
  { key: "coffee_chat",       label: "Coffee Chat",         short: "Coffee",     type: "num"   },
  { key: "called_for_calls",  label: "Called for Calls",    short: "Calls",      type: "num"   },
  { key: "oa_pending",        label: "OA Pending",          short: "OA",         type: "num"   },
  { key: "recruiter_screens", label: "Recruiter Screens",   short: "Recruiter",  type: "num"   },
  { key: "technical_rounds",  label: "Technical Rounds",    short: "Tech",       type: "num"   },
  { key: "final_rounds",      label: "Final Rounds",        short: "Final",      type: "num"   },
  { key: "mocks_done",        label: "Mocks Done",          short: "Mocks",      type: "num"   },
  { key: "notes",             label: "Notes",               short: "Notes",      type: "notes" },
];

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "2-digit", day: "2-digit", year: "2-digit" });
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

export default function ProgressView() {
  const [rows, setRows] = useState<DailyLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editRow, setEditRow] = useState<DailyLogData & { date?: string }>({ date: todayStr() });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const tableRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDailyLogs(90).then((data) => {
      setRows(data);
      // Pre-fill edit row with today's existing entry if present
      const today = data.find((r) => r.date === todayStr());
      if (today) setEditRow({ ...today });
      setLoading(false);
    });
  }, []);

  function setField<K extends keyof DailyLogData>(key: K, value: DailyLogData[K]) {
    setEditRow((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave() {
    setSaving(true);
    try {
      await submitDailyLog({ ...editRow, date: todayStr() });
      // Refresh rows
      const data = await fetchDailyLogs(90);
      setRows(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  }

  const today = todayStr();
  // Merge today's editable row into the display list
  const allRows: (DailyLogEntry & { isToday?: boolean })[] = rows.some((r) => r.date === today)
    ? rows.map((r) => (r.date === today ? { ...editRow, date: today, isToday: true } : r))
    : [{ ...editRow, date: today, isToday: true }, ...rows];

  // Sort ascending by date
  const sorted = [...allRows].sort((a, b) => (a.date ?? "") < (b.date ?? "") ? -1 : 1);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-6 h-6 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin mb-3" />
        <p className="text-xs text-slate-400">Loading progress…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <p className="text-base font-bold text-slate-900">Progress Tracker</p>
          <p className="text-xs text-slate-400 mt-0.5">One row per day — edit today&apos;s row and save.</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-1.5 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
          style={{
            background: saved ? "#16a34a" : "linear-gradient(135deg, #7c3aed, #a78bfa)",
          }}
        >
          {saving ? "Saving…" : saved ? "Saved!" : "Save today"}
        </button>
      </div>

      {/* Scrollable table */}
      <div ref={tableRef} className="flex-1 overflow-auto rounded-2xl" style={{ border: "1px solid #ede9fe" }}>
        <table className="min-w-max w-full text-xs border-collapse">
          <thead>
            <tr style={{ background: "#f5f3ff" }}>
              {/* Sticky: Date */}
              <th
                className="text-left text-[10px] font-semibold text-violet-700 uppercase tracking-[0.08em] px-3 py-2.5 whitespace-nowrap"
                style={{ position: "sticky", left: 0, background: "#f5f3ff", zIndex: 2, borderRight: "1px solid #ede9fe" }}
              >
                Date
              </th>
              {/* Sticky: Day # */}
              <th
                className="text-center text-[10px] font-semibold text-violet-700 uppercase tracking-[0.08em] px-3 py-2.5 whitespace-nowrap"
                style={{ position: "sticky", left: 72, background: "#f5f3ff", zIndex: 2, borderRight: "1px solid #ede9fe" }}
              >
                Day #
              </th>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className="text-center text-[10px] font-semibold text-violet-700 uppercase tracking-[0.08em] px-3 py-2.5 whitespace-nowrap"
                  style={{ borderRight: "1px solid #ede9fe", minWidth: col.type === "notes" ? 200 : col.type === "text" ? 140 : 72 }}
                >
                  {col.short}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, idx) => {
              const isToday = row.date === today;
              const rowBg = isToday ? "#faf9ff" : idx % 2 === 0 ? "#fff" : "#fafafa";
              return (
                <tr key={row.date ?? idx} style={{ background: rowBg }}>
                  {/* Date cell */}
                  <td
                    className="px-3 py-2 font-medium text-slate-700 whitespace-nowrap"
                    style={{
                      position: "sticky",
                      left: 0,
                      background: rowBg,
                      zIndex: 1,
                      borderRight: "1px solid #ede9fe",
                      borderBottom: "1px solid #f1f5f9",
                    }}
                  >
                    <span style={isToday ? { color: "#7c3aed", fontWeight: 700 } : {}}>
                      {row.date ? formatDate(row.date) : "—"}
                    </span>
                    {isToday && (
                      <span className="ml-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "#ede9fe", color: "#7c3aed" }}>
                        TODAY
                      </span>
                    )}
                  </td>
                  {/* Day # cell */}
                  <td
                    className="px-3 py-2 text-center font-semibold text-slate-500 whitespace-nowrap"
                    style={{
                      position: "sticky",
                      left: 72,
                      background: rowBg,
                      zIndex: 1,
                      borderRight: "1px solid #ede9fe",
                      borderBottom: "1px solid #f1f5f9",
                    }}
                  >
                    {idx + 1}
                  </td>
                  {/* Data cells */}
                  {COLUMNS.map((col) => {
                    const val = (row as DailyLogData)[col.key];
                    if (isToday) {
                      if (col.type === "num") {
                        return (
                          <td key={col.key} className="px-2 py-1.5" style={{ borderRight: "1px solid #f1f5f9", borderBottom: "1px solid #f1f5f9" }}>
                            <input
                              type="number"
                              min={0}
                              value={(editRow[col.key] as number) ?? 0}
                              onChange={(e) => setField(col.key as keyof DailyLogData, parseInt(e.target.value) || 0)}
                              className="w-full text-center text-xs font-semibold text-slate-800 rounded-lg px-1.5 py-1 outline-none"
                              style={{ background: "#fff", border: "1.5px solid #ddd6fe", minWidth: 52 }}
                            />
                          </td>
                        );
                      }
                      if (col.type === "text") {
                        return (
                          <td key={col.key} className="px-2 py-1.5" style={{ borderRight: "1px solid #f1f5f9", borderBottom: "1px solid #f1f5f9" }}>
                            <input
                              type="text"
                              value={(editRow[col.key] as string) ?? ""}
                              onChange={(e) => setField(col.key as keyof DailyLogData, e.target.value)}
                              placeholder="—"
                              className="w-full text-xs text-slate-700 rounded-lg px-2 py-1 outline-none"
                              style={{ background: "#fff", border: "1.5px solid #ddd6fe", minWidth: 120 }}
                            />
                          </td>
                        );
                      }
                      // notes
                      return (
                        <td key={col.key} className="px-2 py-1.5" style={{ borderRight: "1px solid #f1f5f9", borderBottom: "1px solid #f1f5f9" }}>
                          <textarea
                            rows={2}
                            value={(editRow[col.key] as string) ?? ""}
                            onChange={(e) => setField(col.key as keyof DailyLogData, e.target.value)}
                            placeholder="Today's notes…"
                            className="w-full text-xs text-slate-700 rounded-lg px-2 py-1 outline-none resize-none"
                            style={{ background: "#fff", border: "1.5px solid #ddd6fe", minWidth: 180 }}
                          />
                        </td>
                      );
                    }

                    // Read-only past row
                    return (
                      <td
                        key={col.key}
                        className="px-3 py-2 text-center text-slate-600 whitespace-nowrap"
                        style={{ borderRight: "1px solid #f1f5f9", borderBottom: "1px solid #f1f5f9", maxWidth: col.type === "notes" ? 200 : undefined }}
                      >
                        {col.type === "num"
                          ? (val as number) > 0
                            ? <span className="font-semibold">{val as number}</span>
                            : <span className="text-slate-300">—</span>
                          : val
                            ? <span className="truncate block max-w-[180px]" title={String(val)}>{String(val)}</span>
                            : <span className="text-slate-300">—</span>
                        }
                      </td>
                    );
                  })}
                </tr>
              );
            })}

            {sorted.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length + 2} className="text-center py-10 text-slate-400 text-xs">
                  No logs yet — fill in today&apos;s row and save to start tracking.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
