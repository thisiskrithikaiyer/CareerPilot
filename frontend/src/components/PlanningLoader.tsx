"use client";

import { useEffect, useState } from "react";
import { AgentEvent } from "@/lib/api";

const STEPS = [
  { label: "Analyzing your situation" },
  { label: "Building your 60-day strategy" },
  { label: "Customizing your daily targets" },
  { label: "Finalizing your dashboard" },
];

const STEP_DELAYS = [0, 3000, 7000, 12000];

export default function PlanningLoader({ agentEvents }: { agentEvents: AgentEvent[] }) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timers = STEP_DELAYS.slice(1).map((delay, i) =>
      setTimeout(() => setActiveStep(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="flex-1 bg-[#FAFAFA] flex flex-col items-center justify-center px-8 h-full">
        <div className="w-full max-w-[340px]">
          {/* Logo */}
          <div className="flex items-center gap-2.5 mb-14">
            <div className="w-7 h-7 rounded-lg bg-violet-700 flex items-center justify-center">
              <span className="text-white text-[10px] font-bold tracking-tight">CP</span>
            </div>
            <span className="text-sm font-semibold text-gray-800 tracking-tight">CareerPilot</span>
          </div>

          {/* Spinner */}
          <div className="relative w-14 h-14 mb-8">
            <div className="absolute inset-0 rounded-full border-[1.5px] border-gray-100" />
            <div className="absolute inset-0 rounded-full border-[1.5px] border-t-violet-600 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          </div>

          <h2 className="text-[20px] font-bold text-gray-900 tracking-tight mb-2">
            Building your plan now
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed mb-10">
            Hang tight — I&apos;m turning your answers into a real, personalized 60-day
            strategy to get you that next offer.
          </p>

          {/* Step indicators */}
          <div className="space-y-4">
            {STEPS.map((step, i) => {
              const done = i < activeStep;
              const active = i === activeStep;
              return (
                <div key={i} className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 border transition-all duration-500 ${
                      done
                        ? "bg-emerald-500 border-emerald-500"
                        : active
                        ? "bg-white border-violet-500"
                        : "bg-white border-gray-200"
                    }`}
                  >
                    {done ? (
                      <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : active ? (
                      <div className="w-2 h-2 rounded-full bg-violet-600 animate-pulse" />
                    ) : null}
                  </div>
                  <span
                    className={`text-[13px] transition-all duration-300 ${
                      done
                        ? "text-gray-400 line-through"
                        : active
                        ? "text-gray-900 font-semibold"
                        : "text-gray-300"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
    </div>
  );
}
