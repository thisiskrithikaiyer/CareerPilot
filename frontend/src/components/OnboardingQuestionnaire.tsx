"use client";

import { useState, useEffect } from "react";
import { IntakeFields } from "@/lib/api";

type Phase = "intro" | "questions" | "extras";

interface Question {
  key: keyof IntakeFields;
  agentLine: string;
  label: string;
  hint?: string;
  options: { value: string; label: string }[];
}

const QUESTIONS: Question[] = [
  {
    key: "role",
    agentLine: "First things first — what kind of engineer are you?",
    label: "Your role",
    options: [
      { value: "SWE", label: "Software Engineer" },
      { value: "MLE", label: "ML Engineer" },
      { value: "AI Engineer", label: "AI Engineer" },
      { value: "Data Engineer", label: "Data Engineer" },
      { value: "Other", label: "Other" },
    ],
  },
  {
    key: "offer_timeline",
    agentLine: "Got it. When are you hoping to land your next offer?",
    label: "What's your timeline to land an offer?",
    options: [
      { value: "1_2_months", label: "ASAP — within 2 months" },
      { value: "3_months", label: "~3 months" },
      { value: "3_6_months", label: "3–6 months" },
      { value: "6_plus", label: "6+ months, no rush" },
    ],
  },
  {
    key: "leetcode_level",
    agentLine: "Last one — this shapes what we practice first so you're ready fast.",
    label: "Where's your coding interview prep right now?",
    options: [
      { value: "cant_do_two_sum", label: "Just getting started" },
      { value: "shaky_mediums", label: "Shaky on mediums" },
      { value: "comfortable_mediums", label: "Solid on mediums" },
      { value: "can_do_hards", label: "Can do hards" },
    ],
  },
];

const STORAGE_KEY = "cc_intake_draft";

function loadDraft(): Partial<IntakeFields> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveDraft(fields: Partial<IntakeFields>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(fields));
  } catch {}
}

function AgentAvatar({ size = "sm" }: { size?: "sm" | "lg" }) {
  const dim = size === "lg" ? "w-16 h-16 rounded-2xl text-lg" : "w-8 h-8 rounded-xl text-[10px]";
  return (
    <div className={`${dim} bg-violet-700 flex items-center justify-center shrink-0 shadow-sm`}>
      <span className="text-white font-bold">CC</span>
    </div>
  );
}

export default function OnboardingQuestionnaire({
  onSubmit,
}: {
  onSubmit: (fields: IntakeFields) => void;
}) {
  const [phase, setPhase] = useState<Phase>("intro");
  const [step, setStep] = useState(0);
  const [fields, setFields] = useState<Partial<IntakeFields>>({});
  const [hydrated, setHydrated] = useState(false);
  const [advancing, setAdvancing] = useState(false);

  useEffect(() => {
    setFields(loadDraft());
    setHydrated(true);
  }, []);

  function setField(key: keyof IntakeFields, value: string | boolean | number) {
    const next = { ...fields, [key]: value };
    setFields(next);
    saveDraft(next);
    return next;
  }

  function pickOption(key: keyof IntakeFields, value: string) {
    setField(key, value);
    setAdvancing(true);
    setTimeout(() => {
      setAdvancing(false);
      if (step < QUESTIONS.length - 1) {
        setStep((s) => s + 1);
      } else {
        setPhase("extras");
      }
    }, 380);
  }

  function handleSubmit() {
    localStorage.removeItem(STORAGE_KEY);
    onSubmit(fields as IntakeFields);
  }

  if (!hydrated) return null;

  // ── Intro ──────────────────────────────────────────────────────────────────
  if (phase === "intro") {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-[400px] text-center">
          <div className="flex justify-center mb-6">
            <AgentAvatar size="lg" />
          </div>

          <h1 className="text-2xl font-bold text-gray-900 tracking-tight mb-3">
            Hey — I&apos;ve got you.
          </h1>
          <p className="text-sm text-gray-500 leading-relaxed mb-2">
            Navigating a career transition is hard. But people who move with
            a clear strategy land offers <span className="text-violet-700 font-semibold">2–3× faster</span> than
            those who wing it.
          </p>
          <p className="text-sm text-gray-500 leading-relaxed mb-10">
            Just a few answers and I&apos;ll have your personalized 60-day plan ready
            to go — built around your situation, not generic advice.
          </p>

          {/* Step preview */}
          <div className="flex justify-center gap-1.5 mb-10">
            {QUESTIONS.map((_, i) => (
              <div key={i} className="h-1.5 w-3 rounded-full bg-gray-200" />
            ))}
          </div>

          <button
            onClick={() => setPhase("questions")}
            className="w-full py-3.5 bg-violet-700 hover:bg-violet-800 text-white font-semibold text-sm rounded-xl transition-all duration-150 shadow-sm"
          >
            Build My Plan →
          </button>
          <p className="text-xs text-gray-400 mt-4">Takes about 60 seconds</p>
        </div>
      </div>
    );
  }

  // ── Step-by-step questions ─────────────────────────────────────────────────
  if (phase === "questions") {
    const q = QUESTIONS[step];
    const selected = fields[q.key];

    return (
      <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
        {/* Nav */}
        <nav className="flex items-center justify-between px-6 py-5 shrink-0">
          <button
            onClick={() => (step === 0 ? setPhase("intro") : setStep((s) => s - 1))}
            className="text-xs text-gray-400 hover:text-gray-600 transition flex items-center gap-1"
          >
            ← Back
          </button>

          <div className="flex items-center gap-1.5">
            {QUESTIONS.map((_, i) => (
              <div
                key={i}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i < step
                    ? "w-6 bg-violet-600"
                    : i === step
                    ? "w-6 bg-violet-300"
                    : "w-3 bg-gray-200"
                }`}
              />
            ))}
          </div>

          <span className="text-xs text-gray-400 font-medium tabular-nums">
            {step + 1} / {QUESTIONS.length}
          </span>
        </nav>

        {/* Content */}
        <div className="flex-1 flex flex-col justify-center items-center px-6 pb-20">
          <div className="w-full max-w-[480px]">
            {/* Agent speech bubble */}
            <div className="flex items-start gap-3 mb-8">
              <AgentAvatar />
              <div className="bg-white border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm max-w-xs">
                <p className="text-sm text-gray-700 leading-relaxed">{q.agentLine}</p>
              </div>
            </div>

            {/* Question */}
            <h2 className="text-[22px] font-bold text-gray-900 tracking-tight mb-1.5">
              {q.label}
            </h2>
            {q.hint && (
              <p className="text-sm text-gray-400 mb-6">{q.hint}</p>
            )}
            {!q.hint && <div className="mb-6" />}

            {/* Options */}
            <div className="flex flex-col gap-2.5">
              {q.options.map((opt) => {
                const isSelected = selected === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => !advancing && pickOption(q.key, opt.value)}
                    disabled={advancing}
                    className={`w-full text-left px-5 py-3.5 rounded-xl border text-sm font-medium transition-all duration-150 ${
                      isSelected
                        ? "bg-violet-700 border-violet-700 text-white shadow-md scale-[1.01]"
                        : "bg-white border-gray-200 text-gray-700 hover:border-violet-300 hover:text-violet-700 hover:shadow-sm"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Extras (optional) ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <nav className="flex items-center justify-between px-6 py-5 shrink-0">
        <button
          onClick={() => { setStep(QUESTIONS.length - 1); setPhase("questions"); }}
          className="text-xs text-gray-400 hover:text-gray-600 transition flex items-center gap-1"
        >
          ← Back
        </button>

        <div className="flex items-center gap-1.5">
          {QUESTIONS.map((_, i) => (
            <div key={i} className="h-1.5 w-6 rounded-full bg-violet-600" />
          ))}
          <div className="h-1.5 w-6 rounded-full bg-violet-300" />
        </div>

        <span className="text-xs text-gray-400 font-medium">Almost done</span>
      </nav>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[500px] mx-auto px-6 py-4">
          {/* Agent message */}
          <div className="flex items-start gap-3 mb-8">
            <AgentAvatar />
            <div className="bg-white border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <p className="text-sm text-gray-700 leading-relaxed">
                Two optional things that will make your plan significantly sharper — add
                what you can.
              </p>
            </div>
          </div>

          <h2 className="text-[20px] font-bold text-gray-900 tracking-tight mb-6">
            Almost there.
          </h2>

          <div className="space-y-4">
            {/* Resume */}
            <div
              className={`bg-white rounded-2xl p-5 border shadow-sm transition-all duration-200 ${
                fields.resume_text ? "border-violet-100" : "border-gray-100"
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-[13px] font-semibold text-gray-900">Paste your resume</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Helps me tailor your plan to your actual experience
                  </p>
                </div>
                <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full font-medium">
                  Optional
                </span>
              </div>
              <textarea
                rows={7}
                placeholder="Work experience, skills, education…"
                value={fields.resume_text ?? ""}
                onChange={(e) => setField("resume_text", e.target.value)}
                className="w-full px-3.5 py-3 border border-gray-200 rounded-xl text-xs text-gray-700 leading-relaxed placeholder-gray-300 focus:outline-none focus:border-violet-300 focus:ring-1 focus:ring-violet-100 transition resize-none"
              />
            </div>
          </div>

          {/* CTA */}
          <div className="mt-8 mb-16">
            <button
              onClick={handleSubmit}
              className="w-full py-3.5 bg-violet-700 hover:bg-violet-800 text-white font-semibold text-sm rounded-xl transition-all duration-150 shadow-sm"
            >
              Build My 60-Day Plan →
            </button>
            <p className="text-xs text-center text-gray-400 mt-3">
              Your plan will be ready in under a minute
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
