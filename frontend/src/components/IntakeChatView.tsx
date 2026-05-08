"use client";

import { useEffect, useRef, useState } from "react";
import { AgentEvent, IntakeFields, Message, streamIntake, IntakeStepEvent } from "@/lib/api";

interface Props {
  onAgentEvent: (event: AgentEvent) => void;
  onComplete: (fields: Partial<IntakeFields>) => void;
  onLoadingChange?: (loading: boolean) => void;
}

function AgentAvatar({ size = "sm" }: { size?: "sm" | "lg" }) {
  const dim = size === "lg" ? "w-16 h-16 rounded-2xl text-lg" : "w-8 h-8 rounded-xl text-[10px]";
  return (
    <div className={`${dim} bg-violet-700 flex items-center justify-center shrink-0 shadow-sm`}>
      <span className="text-white font-bold">CP</span>
    </div>
  );
}

const PROGRESS_KEYS = ["role", "offer_timeline", "leetcode_level"];

export default function IntakeChatView({ onAgentEvent, onComplete, onLoadingChange }: Props) {
  const [step, setStep] = useState<IntakeStepEvent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [picking, setPicking] = useState(false);
  const [collectedFields, setCollectedFields] = useState<Partial<IntakeFields>>({});
  const [pendingComplete, setPendingComplete] = useState<Partial<IntakeFields> | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [freeText, setFreeText] = useState("");

  // Ref holds the authoritative message history — avoids stale closure in async callbacks
  const historyRef = useRef<Message[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  async function fireAgent(msgs: Message[], latestFields: Partial<IntakeFields>) {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setIsLoading(true);
    onLoadingChange?.(true);

    let agentReply = "";

    try {
      await streamIntake(msgs, latestFields, (event) => {
        if (event.type === "agent_event") {
          onAgentEvent({
            agent: event.agent!,
            display_name: event.display_name!,
            reason: event.reason!,
            timestamp: event.timestamp!,
          });
        } else if (event.type === "step") {
          const s = event as IntakeStepEvent;
          agentReply = s.reply;
          setStep(s);
          if (s.intake_complete) {
            setPendingComplete(latestFields);
          }
        } else if (event.type === "error") {
          setErrorMsg((event as { type: "error"; message: string }).message);
        }
      }, ctrl.signal);
    } finally {
      if (ctrl.signal.aborted) return;
      if (agentReply) {
        historyRef.current = [...msgs, { role: "assistant", content: agentReply }];
      }
      setIsLoading(false);
      setPicking(false);
      onLoadingChange?.(false);
    }
  }

  useEffect(() => {
    fireAgent([], {}).catch(() => {});
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handlePick(opt: { value: string; label: string }) {
    if (picking || isLoading || !step?.field_key) return;
    setPicking(true);

    const newMessages: Message[] = [
      ...historyRef.current,
      { role: "user", content: opt.label },
    ];
    historyRef.current = newMessages;

    const fieldKey = step.field_key as keyof IntakeFields;
    const value = opt.value;
    const updated = { ...collectedFields, [fieldKey]: value };
    setCollectedFields(updated);

    fireAgent(newMessages, updated);
  }

  function handleFreeTextSubmit() {
    const text = freeText.trim();
    if (!text || picking || isLoading) return;
    setFreeText("");
    if (step?.field_key === "notes") {
      handleNotesSubmit(text);
    } else {
      handleChipClick(text);
    }
  }

  function handleChipClick(chip: string) {
    if (picking || isLoading) return;
    if (step?.field_key === "notes") {
      handleNotesSubmit(chip);
      return;
    }
    setPicking(true);
    const newMessages: Message[] = [
      ...historyRef.current,
      { role: "user", content: chip },
    ];
    historyRef.current = newMessages;
    fireAgent(newMessages, collectedFields);
  }

  function handleNotesSubmit(text: string) {
    if (picking || isLoading) return;
    setPicking(true);
    const noteValue = text === "Skip — that's all" ? "skip" : text;
    const newMessages: Message[] = [
      ...historyRef.current,
      { role: "user", content: text },
    ];
    historyRef.current = newMessages;
    const updated = { ...collectedFields, notes: noteValue };
    setCollectedFields(updated);
    fireAgent(newMessages, updated);
  }

  // ── Intro loading state ───────────────────────────────────────────────────
  if (isLoading && !step) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-[400px] text-center">
          <div className="flex justify-center mb-6"><AgentAvatar size="lg" /></div>
          <p className="text-sm text-gray-500 animate-pulse">Getting your intake ready…</p>
        </div>
      </div>
    );
  }

  if (errorMsg) {
    const isRateLimit = errorMsg.includes("Rate limit") || errorMsg.includes("rate_limit") || errorMsg.includes("429");
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-[400px] text-center">
          <div className="flex justify-center mb-6"><AgentAvatar size="lg" /></div>
          <p className="text-sm font-semibold text-gray-800 mb-2">
            {isRateLimit ? "Too many requests — please try again in a few minutes" : "Something went wrong"}
          </p>
          <p className="text-xs text-gray-400 mb-6">
            {isRateLimit ? "The AI model hit its daily limit. It resets shortly." : errorMsg}
          </p>
          <button
            onClick={() => { setErrorMsg(null); setIsLoading(true); fireAgent([], {}).catch(() => {}); }}
            className="px-6 py-2.5 bg-violet-700 hover:bg-violet-800 text-white text-sm font-semibold rounded-xl transition-all"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!step) return null;

  // ── Intake complete — show final message + continue ───────────────────────
  if (pendingComplete) {
    return (
      <div className="min-h-screen bg-[#FAFAFA] flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-[400px]">
          <div className="flex items-start gap-3 mb-8">
            <AgentAvatar />
            <div className="bg-white border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <p className="text-sm text-gray-700 leading-relaxed">{step.reply}</p>
            </div>
          </div>
          <button
            onClick={() => onComplete(pendingComplete)}
            className="w-full py-3.5 bg-violet-700 hover:bg-violet-800 text-white font-semibold text-sm rounded-xl transition-all duration-150 shadow-sm"
          >
            Build My 60-Day Plan →
          </button>
        </div>
      </div>
    );
  }

  const hasOptions = step.options.length > 0;
  const hasChips = step.chips.length > 0;

  // ── Active question card ──────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <nav className="flex items-center justify-center px-6 py-5 shrink-0 gap-1.5">
        {PROGRESS_KEYS.map((key) => {
          const done = collectedFields[key as keyof IntakeFields] !== undefined;
          const active = step.field_key === key;
          return (
            <div
              key={key}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                done ? "w-6 bg-violet-600" : active ? "w-6 bg-violet-300" : "w-3 bg-gray-200"
              }`}
            />
          );
        })}
      </nav>

      <div className="flex-1 flex flex-col justify-center items-center px-6 pb-20">
        <div className="w-full max-w-[480px]">
          {/* Agent speech bubble */}
          <div className="flex items-start gap-3 mb-8">
            <AgentAvatar />
            <div className="bg-white border border-violet-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm max-w-xs">
              {isLoading ? (
                <div className="flex gap-1 items-center h-5">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              ) : (
                <p className="text-sm text-gray-700 leading-relaxed">{step.reply}</p>
              )}
            </div>
          </div>

          {!isLoading && (
            <>
              {/* Notes phase: always show text input + Skip chip */}
              {step.field_key === "notes" ? (
                <div className="flex flex-col gap-3 mt-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={freeText}
                      onChange={(e) => setFreeText(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleFreeTextSubmit()}
                      placeholder="Visa status, relocation, target companies…"
                      disabled={picking}
                      className="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-violet-400 disabled:opacity-50"
                    />
                    <button
                      onClick={handleFreeTextSubmit}
                      disabled={picking || !freeText.trim()}
                      className="px-4 py-3 bg-violet-700 hover:bg-violet-800 disabled:opacity-40 text-white text-sm font-semibold rounded-xl transition-all duration-150"
                    >
                      →
                    </button>
                  </div>
                  <button
                    onClick={() => handleChipClick("Skip — that's all")}
                    disabled={picking}
                    className={`self-start px-4 py-2 rounded-full border text-sm font-medium transition-all duration-150 ${
                      picking
                        ? "opacity-50 cursor-not-allowed bg-white border-gray-200 text-gray-400"
                        : "bg-white border-violet-200 text-violet-700 hover:bg-violet-50 hover:border-violet-400"
                    }`}
                  >
                    Skip — that&apos;s all
                  </button>
                </div>
              ) : (
                <>
                  {hasOptions && (
                    <div className="flex flex-col gap-2.5">
                      {step.options.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => handlePick(opt)}
                          disabled={picking}
                          className={`w-full text-left px-5 py-3.5 rounded-xl border text-sm font-medium transition-all duration-150 ${
                            picking
                              ? "opacity-50 cursor-not-allowed bg-white border-gray-200 text-gray-500"
                              : "bg-white border-gray-200 text-gray-700 hover:border-violet-300 hover:text-violet-700 hover:shadow-sm"
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}

                  {hasChips && (
                    <div className={`flex flex-wrap gap-2 ${hasOptions ? "mt-4" : "mt-2"}`}>
                      {step.chips.map((chip) => (
                        <button
                          key={chip}
                          onClick={() => handleChipClick(chip)}
                          disabled={picking}
                          className={`px-4 py-2 rounded-full border text-sm font-medium transition-all duration-150 ${
                            hasOptions ? "text-xs px-3 py-1.5" : ""
                          } ${
                            picking
                              ? "opacity-50 cursor-not-allowed bg-white border-gray-200 text-gray-400"
                              : "bg-white border-violet-200 text-violet-700 hover:bg-violet-50 hover:border-violet-400"
                          }`}
                        >
                          {chip}
                        </button>
                      ))}
                    </div>
                  )}

                  {!hasChips && !hasOptions && (
                    <div className="flex gap-2 mt-2">
                      <input
                        type="text"
                        value={freeText}
                        onChange={(e) => setFreeText(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleFreeTextSubmit()}
                        placeholder="Type your answer…"
                        disabled={picking}
                        className="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-violet-400 disabled:opacity-50"
                      />
                      <button
                        onClick={handleFreeTextSubmit}
                        disabled={picking || !freeText.trim()}
                        className="px-4 py-3 bg-violet-700 hover:bg-violet-800 disabled:opacity-40 text-white text-sm font-semibold rounded-xl transition-all duration-150"
                      >
                        →
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
