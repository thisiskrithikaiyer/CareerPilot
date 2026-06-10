"use client";

import { useState, useEffect } from "react";
import CoachView from "@/components/CoachView";
import TodayPlanView from "@/components/TodayPlanView";
import ProgressView from "@/components/ProgressView";
import AuthScreen from "@/components/AuthScreen";
import AgentFlowPanel from "@/components/AgentFlowPanel";
import IntakeChatView from "@/components/IntakeChatView";
import ExtrasForm from "@/components/ExtrasForm";
import PlanningLoader from "@/components/PlanningLoader";
import PlanVerdictView from "@/components/PlanVerdictView";
import {
  getToken,
  clearToken,
  AgentEvent,
  GoalPlan,
  IntakeFields,
  submitIntake,
  getIntakeStatus,
  streamChat,
  fetchGoalPlan,
  generatePlanForDate,
  getSessionDate,
  advanceSessionDate,
} from "@/lib/api";

type AppView = "questionnaire" | "extras" | "loading" | "verdict" | "dashboard";
type DashTab = "today" | "progress";

export default function Home() {
  const [hydrated, setHydrated] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [view, setView] = useState<AppView>("questionnaire");
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [pendingPlan, setPendingPlan] = useState<GoalPlan | null>(null);
  const [intakeFields, setIntakeFields] = useState<Partial<IntakeFields>>({});
  const [planRefreshKey, setPlanRefreshKey] = useState(0);
  const [dashTab, setDashTab] = useState<DashTab>("today");
  const [sessionDate, setSessionDate] = useState<string>(() => getSessionDate());

  async function resolveView() {
    try {
      const status = await getIntakeStatus();
      setView(status.intake_complete ? "dashboard" : "questionnaire");
    } catch {
      setView("questionnaire");
    }
  }

  useEffect(() => {
    if (!getToken()) {
      setHydrated(true);
      return;
    }
    setAuthed(true);
    resolveView().then(() => setHydrated(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleAuth() {
    setAuthed(true);
    await resolveView();
  }

  // Called by IntakeChatView when agent marks intake_complete
  function handleIntakeQuestionsComplete(fields: Partial<IntakeFields>) {
    setIntakeFields(fields);
    setView("extras");
  }

  // Called when user submits the extras form (resume)
  async function handleExtrasSubmit(extras: Partial<IntakeFields>) {
    const merged = { ...intakeFields, ...extras } as IntakeFields;
    if (!merged.role || !merged.offer_timeline) {
      console.error("[intake] missing required fields, resetting to questionnaire", merged);
      setView("questionnaire");
      return;
    }
    setView("loading");
    setChatLoading(true);
    // Keep existing intake agent events — don't wipe history

    try {
      await submitIntake(merged);

      // Use streamChat so agent routing events hit the panel in real time
      await streamChat(
        [{ role: "user", content: "I've completed my intake. Please build my personalized 60-day career plan now." }],
        (event) => {
          if (event.type === "agent_event") {
            setAgentEvents((prev) => [...prev, {
              agent: event.agent!,
              display_name: event.display_name!,
              reason: event.reason!,
              timestamp: event.timestamp!,
            }]);
          }
        },
      );

      const plan = await fetchGoalPlan();
      if (plan) {
        setPendingPlan(plan);
        setView("verdict");
        return;
      }
    } catch (e) {
      console.error("[onboarding] plan generation error:", e);
    } finally {
      setChatLoading(false);
    }

    setView("dashboard");
  }

  async function handleAdvanceDay() {
    const tomorrow = advanceSessionDate();
    setSessionDate(tomorrow);
    await generatePlanForDate(tomorrow);
    setPlanRefreshKey((k) => k + 1);
  }

  function handleSignOut() {
    clearToken();
    setAuthed(false);
    setView("questionnaire");
    setAgentEvents([]);
    setPendingPlan(null);
    setIntakeFields({});
  }

  if (!hydrated) return null;

  if (!authed) {
    return <AuthScreen onAuth={handleAuth} />;
  }

  // ── Persistent post-login layout: content left + dark agent panel right ────
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left: view content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {view === "questionnaire" && (
          <div className="flex-1 overflow-y-auto">
            <IntakeChatView
              onAgentEvent={(ev) => setAgentEvents((prev) => [...prev, ev])}
              onComplete={handleIntakeQuestionsComplete}
              onLoadingChange={setChatLoading}
            />
          </div>
        )}

        {view === "extras" && (
          <div className="flex-1 overflow-y-auto">
            <ExtrasForm
              onSubmit={handleExtrasSubmit}
              onSkip={() => handleExtrasSubmit({})}
            />
          </div>
        )}

        {view === "loading" && (
          <PlanningLoader agentEvents={agentEvents} />
        )}

        {view === "verdict" && pendingPlan && (
          <div className="flex-1 overflow-y-auto">
            <PlanVerdictView
              plan={pendingPlan}
              onAgentEvents={(evs) => setAgentEvents((prev) => [...prev, ...evs])}
              onCommit={() => {
                setPendingPlan(null);
                setPlanRefreshKey((k) => k + 1);
                setView("dashboard");
              }}
            />
          </div>
        )}

        {view === "dashboard" && (
          <>
            {/* Top bar */}
            <header className="flex items-center gap-3 px-6 py-3.5 shrink-0" style={{ background: "#fff", borderBottom: "1px solid #ede9fe" }}>
              <div className="w-7 h-7 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg, #7c3aed, #a78bfa)" }}>
                <span className="text-white text-[10px] font-bold tracking-tight">CP</span>
              </div>
              <div className="flex-1">
                <h1 className="text-sm font-semibold text-slate-800">CareerPilot</h1>
                <p className="text-[11px] text-slate-400">
                  {new Date(sessionDate + "T00:00:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
                </p>
              </div>
              <button onClick={handleSignOut} className="text-xs text-slate-400 hover:text-violet-600 transition-colors">
                Sign out
              </button>
            </header>

            {/* Tab nav */}
            <nav className="flex gap-1 px-6 pt-3 pb-0 shrink-0" style={{ borderBottom: "1px solid #f1f5f9" }}>
              {(["today", "progress"] as DashTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDashTab(tab)}
                  className="px-4 py-2 text-xs font-semibold capitalize transition-all rounded-t-lg"
                  style={
                    dashTab === tab
                      ? { color: "#7c3aed", borderBottom: "2px solid #7c3aed", background: "#faf9ff" }
                      : { color: "#94a3b8", borderBottom: "2px solid transparent" }
                  }
                >
                  {tab}
                </button>
              ))}
            </nav>

            {/* Tab content */}
            {dashTab === "today" && (
              <>
                <div className="flex-1 overflow-y-auto px-6 pt-6">
                  <TodayPlanView key={planRefreshKey} sessionDate={sessionDate} onAdvanceDay={handleAdvanceDay} />
                </div>
                <CoachView
                  sessionDate={sessionDate}
                  onAuthError={handleSignOut}
                  onAgentEvents={(evs) => setAgentEvents((prev) => [...prev, ...evs])}
                  onLoadingChange={setChatLoading}
                  onCommitted={() => setPlanRefreshKey((k) => k + 1)}
                />
              </>
            )}

            {dashTab === "progress" && (
              <div className="flex-1 overflow-hidden px-6 pt-6 pb-6">
                <ProgressView sessionDate={sessionDate} />
              </div>
            )}
          </>
        )}
      </div>

      {/* Right: always-on dark agent activity panel */}
      <div className="w-60 shrink-0 overflow-hidden">
        <AgentFlowPanel events={agentEvents} isLoading={chatLoading} />
      </div>
    </div>
  );
}
