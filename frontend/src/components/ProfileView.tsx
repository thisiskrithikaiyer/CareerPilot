"use client";

import { useState } from "react";
import { saveResume, saveLinkedIn } from "@/lib/api";

interface UploadCardProps {
  title: string;
  hint: string;
  placeholder: string;
  icon: string;
  onSave: (text: string) => Promise<void>;
}

function UploadCard({ title, hint, placeholder, icon, onSave }: UploadCardProps) {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(text.trim());
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl overflow-hidden bg-white" style={{ border: "1px solid #ede9fe" }}>
      <div className="px-4 py-3 flex items-center gap-2" style={{ background: "#f5f3ff" }}>
        <span className="text-sm">{icon}</span>
        <div>
          <p className="text-xs font-semibold text-violet-700 uppercase tracking-[0.1em]">{title}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">{hint}</p>
        </div>
      </div>
      <div className="px-4 py-4 space-y-3">
        <textarea
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder}
          className="w-full text-xs text-slate-700 rounded-xl px-3 py-2.5 outline-none resize-none leading-relaxed"
          style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}
        />
        {error && <p className="text-xs text-rose-500">{error}</p>}
        <div className="flex items-center justify-between">
          <p className="text-[10px] text-slate-300">{text.trim() ? `${text.trim().length.toLocaleString()} characters` : ""}</p>
          <button
            onClick={handleSave}
            disabled={saving || !text.trim()}
            className="px-5 py-2 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-40"
            style={{ background: saved ? "#16a34a" : "linear-gradient(135deg, #7c3aed, #a78bfa)" }}
          >
            {saving ? "Analyzing…" : saved ? "Saved — re-scoring skills" : `Save ${title.toLowerCase()}`}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProfileView() {
  return (
    <div className="space-y-5 pb-6">
      <div>
        <p className="text-base font-bold text-slate-900">Profile</p>
        <p className="text-xs text-slate-400 mt-0.5">
          Paste your latest resume or LinkedIn — the Talent Mapper re-scores your skill map within seconds.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <UploadCard
          title="Resume"
          icon="📄"
          hint="Paste the full plain text of your resume."
          placeholder={"JANE DOE\nML Engineer, 4 yrs\n\nEXPERIENCE\n…"}
          onSave={saveResume}
        />
        <UploadCard
          title="LinkedIn"
          icon="💼"
          hint="Paste your About section, headline, and experience."
          placeholder={"About: ML engineer with 4 years building…"}
          onSave={saveLinkedIn}
        />
      </div>
    </div>
  );
}
