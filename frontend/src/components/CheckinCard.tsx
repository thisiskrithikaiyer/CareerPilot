"use client";

import { useState } from "react";
import { submitCheckin, CheckinResponse } from "@/lib/api";

const MOOD_EMOJI = ["😖", "😞", "😕", "😐", "🙂", "😊", "😄", "😁", "🤩", "🚀"];
const ENERGY_EMOJI = ["🪫", "🪫", "😴", "😪", "😌", "🙂", "💪", "⚡", "⚡", "🔥"];

function scoreLabel(score: number, kind: "mood" | "energy") {
  if (kind === "mood") {
    if (score <= 3) return "Rough day";
    if (score <= 5) return "Hanging in";
    if (score <= 7) return "Doing okay";
    return "Feeling great";
  }
  if (score <= 3) return "Running on empty";
  if (score <= 5) return "Low battery";
  if (score <= 7) return "Steady";
  return "Fully charged";
}

interface TagInputProps {
  label: string;
  placeholder: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  accent: string;
  bg: string;
}

function TagInput({ label, placeholder, tags, onChange, accent, bg }: TagInputProps) {
  const [draft, setDraft] = useState("");

  function commit() {
    const v = draft.trim();
    if (!v) return;
    onChange([...tags, v]);
    setDraft("");
  }

  return (
    <div>
      <label className="text-[10px] text-slate-400 block mb-1.5">{label}</label>
      <div
        className="flex flex-wrap items-center gap-1.5 rounded-xl px-2.5 py-2"
        style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
      >
        {tags.map((tag, i) => (
          <span
            key={`${tag}-${i}`}
            className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full"
            style={{ background: bg, color: accent }}
          >
            {tag}
            <button
              onClick={() => onChange(tags.filter((_, j) => j !== i))}
              className="opacity-50 hover:opacity-100 transition-opacity leading-none"
              aria-label={`Remove ${tag}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          placeholder={tags.length === 0 ? placeholder : "Add another…"}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); commit(); }
            if (e.key === "Backspace" && !draft && tags.length) onChange(tags.slice(0, -1));
          }}
          onBlur={commit}
          className="flex-1 min-w-[120px] text-xs text-slate-700 bg-transparent outline-none py-0.5"
        />
      </div>
    </div>
  );
}

interface Props {
  onComplete: (response: CheckinResponse) => void;
}

export default function CheckinCard({ onComplete }: Props) {
  const [mood, setMood] = useState(6);
  const [energy, setEnergy] = useState(6);
  const [wins, setWins] = useState<string[]>([]);
  const [blockers, setBlockers] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitCheckin({
        mood_score: mood,
        energy_score: energy,
        wins: wins.length ? wins : undefined,
        blockers: blockers.length ? blockers : undefined,
        notes: notes.trim() || undefined,
      });
      onComplete(res);
    } catch {
      setError("Couldn't save your check-in. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid #ede9fe", animation: "checkinIn 0.4s ease both" }}>
      <div className="px-4 py-3" style={{ background: "#f5f3ff" }}>
        <p className="text-xs font-semibold text-violet-700 uppercase tracking-[0.1em]">Evening Check-in</p>
        <p className="text-[11px] text-slate-400 mt-0.5">
          How are you holding up? Your coach uses this to shape tomorrow&apos;s plan.
        </p>
      </div>

      <div className="px-4 py-4 space-y-5 bg-white">
        {/* Sliders */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {([
            ["Mood", mood, setMood, MOOD_EMOJI, "mood"],
            ["Energy", energy, setEnergy, ENERGY_EMOJI, "energy"],
          ] as [string, number, (v: number) => void, string[], "mood" | "energy"][]).map(
            ([label, value, setter, emojis, kind]) => (
              <div key={label}>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[10px] text-slate-400">{label}</label>
                  <span className="text-[11px] font-semibold text-violet-600">
                    {emojis[value - 1]} {value}/10 · {scoreLabel(value, kind)}
                  </span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={value}
                  onChange={(e) => setter(parseInt(e.target.value))}
                  className="w-full checkin-slider"
                />
              </div>
            ),
          )}
        </div>

        <TagInput
          label="Wins today"
          placeholder="e.g. Finished 3 leetcode mediums"
          tags={wins}
          onChange={setWins}
          accent="#16a34a"
          bg="#f0fdf4"
        />

        <TagInput
          label="Blockers"
          placeholder="e.g. Anxious about Friday's onsite"
          tags={blockers}
          onChange={setBlockers}
          accent="#dc2626"
          bg="#fef2f2"
        />

        <div>
          <label className="text-[10px] text-slate-400 block mb-1">Anything else?</label>
          <textarea
            rows={2}
            placeholder="Slept badly, recruiter ghosted, feeling hopeful…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full text-xs text-slate-700 rounded-lg px-2.5 py-2 outline-none resize-none"
            style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
          />
        </div>

        {error && <p className="text-xs text-rose-500">{error}</p>}

        <div className="flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-5 py-2 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
          >
            {submitting ? "Checking in…" : "Check in with coach"}
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes checkinIn {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .checkin-slider {
          -webkit-appearance: none;
          appearance: none;
          height: 6px;
          border-radius: 9999px;
          background: linear-gradient(90deg, #ddd6fe, #a78bfa);
          outline: none;
        }
        .checkin-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #7c3aed;
          border: 3px solid #fff;
          box-shadow: 0 1px 4px rgba(124, 58, 237, 0.4);
          cursor: pointer;
        }
        .checkin-slider::-moz-range-thumb {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #7c3aed;
          border: 3px solid #fff;
          box-shadow: 0 1px 4px rgba(124, 58, 237, 0.4);
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}
