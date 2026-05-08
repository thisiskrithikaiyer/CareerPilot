"use client";

const CHIPS = [
  { label: "I want to land a new role", icon: "🎯" },
  { label: "Between jobs", icon: "💼" },
  { label: "Switching industries", icon: "🔄" },
  { label: "Targeting Big Tech", icon: "🏢" },
  { label: "Need to level up my skills", icon: "📈" },
  { label: "Struggling with interviews", icon: "🎤" },
  { label: "Not getting callbacks", icon: "📬" },
  { label: "Just starting my search", icon: "🚀" },
];

export default function OnboardingWelcome({
  onChipClick,
}: {
  onChipClick: (text: string) => void;
}) {
  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-white">
      {/* Hero */}
      <div className="px-8 pt-10 pb-7">
        <span className="inline-block text-xs font-semibold tracking-widest text-violet-500 uppercase mb-3">
          AI job coaching platform
        </span>
        <h2 className="text-2xl font-bold text-gray-900 leading-snug mb-2.5">
          Let&apos;s land your next role.
        </h2>
        <p className="text-sm text-gray-500 leading-relaxed max-w-lg">
          I&apos;m your AI job coach. Tell me your target role and timeline, and I&apos;ll build a personalized plan — then schedule every single day around hitting that goal.
        </p>
        <p className="text-sm text-gray-500 leading-relaxed max-w-lg mt-3">
          No generic advice. I&apos;ll ask the right questions, learn your situation, and give you a focused daily schedule: what to study, what to apply to, and what to work on — in priority order.
        </p>
      </div>

      <div className="mx-8 h-px bg-gray-100" />

      {/* Chips */}
      <div className="px-8 pt-6 pb-6 flex-1 overflow-y-auto">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
          What&apos;s your situation?
        </p>
        <div className="flex flex-wrap gap-2.5">
          {CHIPS.map(({ label, icon }) => (
            <button
              key={label}
              onClick={() => onChipClick(label)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full border border-gray-200 bg-white text-gray-700 text-sm font-medium hover:border-violet-600 hover:text-violet-700 hover:bg-violet-50 transition-all duration-150 shadow-sm"
            >
              <span className="text-base leading-none">{icon}</span>
              {label}
            </button>
          ))}
        </div>

        <p className="mt-7 text-xs text-gray-400">
          Pick one to get started, or just describe your goal — I&apos;ll take it from there and build your schedule.
        </p>
      </div>
    </div>
  );
}
