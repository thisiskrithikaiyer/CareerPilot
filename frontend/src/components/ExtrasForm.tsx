"use client";

import { useState } from "react";
import { IntakeFields } from "@/lib/api";

interface Props {
  onSubmit: (extras: Partial<IntakeFields>) => void;
  onSkip: () => void;
}

function AgentAvatar() {
  return (
    <div className="w-8 h-8 rounded-xl bg-violet-700 flex items-center justify-center shrink-0 shadow-sm">
      <span className="text-white font-bold text-[10px]">CC</span>
    </div>
  );
}

export default function ExtrasForm({ onSubmit, onSkip }: Props) {
  const [resumeText, setResumeText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleSubmit() {
    setSubmitting(true);
    const extras: Partial<IntakeFields> = {};
    if (resumeText.trim()) extras.resume_text = resumeText.trim();
    onSubmit(extras);
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <nav className="flex items-center justify-between px-6 py-5 shrink-0">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-1.5 w-6 rounded-full bg-violet-600" />
          ))}
          <div className="h-1.5 w-6 rounded-full bg-violet-300" />
        </div>
        <span className="text-xs text-gray-400 font-medium">Almost done</span>
      </nav>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[500px] mx-auto px-6 py-4">
          <div className="flex items-start gap-3 mb-8">
            <AgentAvatar />
            <div className="bg-white border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <p className="text-sm text-gray-700 leading-relaxed">
                Two optional things that will make your plan significantly sharper — add what you can.
              </p>
            </div>
          </div>

          <h2 className="text-[20px] font-bold text-gray-900 tracking-tight mb-6">Almost there.</h2>

          <div className="space-y-4">
            {/* Resume */}
            <div className={`bg-white rounded-2xl p-5 border shadow-sm transition-all duration-200 ${resumeText ? "border-violet-100" : "border-gray-100"}`}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-[13px] font-semibold text-gray-900">Paste your resume</p>
                  <p className="text-xs text-gray-400 mt-0.5">Helps me tailor your plan to your actual experience</p>
                </div>
                <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full font-medium">Optional</span>
              </div>
              <textarea
                rows={7}
                placeholder="Work experience, skills, education…"
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                className="w-full px-3.5 py-3 border border-gray-200 rounded-xl text-xs text-gray-700 leading-relaxed placeholder-gray-300 focus:outline-none focus:border-violet-300 focus:ring-1 focus:ring-violet-100 transition resize-none"
              />
            </div>
          </div>

          <div className="mt-8 mb-16 space-y-3">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full py-3.5 bg-violet-700 hover:bg-violet-800 disabled:opacity-60 text-white font-semibold text-sm rounded-xl transition-all duration-150 shadow-sm"
            >
              {submitting ? "Building your plan…" : "Build My 60-Day Plan →"}
            </button>
            <button
              onClick={onSkip}
              disabled={submitting}
              className="w-full py-2 text-xs text-gray-400 hover:text-gray-600 transition"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
