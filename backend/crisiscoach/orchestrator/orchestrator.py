"""Orchestrator node — loads context, runs supervisor, delegates to agent."""
from datetime import datetime, timezone
from crisiscoach.orchestrator.state import CrisisCoachState
from crisiscoach.orchestrator.supervisor import decide
from crisiscoach.orchestrator.context_builder import build_context


AGENT_MAP = {
    "intake":         "crisiscoach.agents.runtime.intake",
    "goal_planner":   "crisiscoach.agents.runtime.goal_planner",
    "checkin":        "crisiscoach.agents.runtime.daily_tracker",
    "plan":           "crisiscoach.agents.runtime.accountability",
    "accountability": "crisiscoach.agents.runtime.accountability",
    "mental_health":  "crisiscoach.agents.runtime.mental_health_check",
    "chat":           "crisiscoach.agents.runtime.mental_health_check",
}

AGENT_DISPLAY_NAMES = {
    "intake":       "Intake Coach",
    "goal_planner": "Goal Strategist",
    "checkin":      "Daily Tracker",
    "plan":         "Accountability Coach",
    "accountability": "Accountability Coach",
    "mental_health": "Wellness Coach",
    "chat":         "Coach",
}


async def orchestrator_node(state: CrisisCoachState) -> dict:
    # 1. Load DB context (phase, intake_complete, runway, etc.) BEFORE supervisor decides
    ctx = await build_context(state)
    enriched = {**state, **ctx}

    # 2. Supervisor decides which agent runs
    intent, reason = decide(enriched)

    # 3. Re-fetch with intent for agents that need heavy data (resume, tracking)
    if intent == "goal_planner":
        ctx = await build_context(state, intent=intent)

    agent_module = AGENT_MAP.get(intent, AGENT_MAP["chat"])

    event = {
        "agent": intent,
        "display_name": AGENT_DISPLAY_NAMES.get(intent, "Coach"),
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    prior_events = state.get("agent_events") or []

    return {
        **ctx,
        "intent": intent,
        "agent": agent_module,
        "agent_display": AGENT_DISPLAY_NAMES.get(intent, "Coach"),
        "agent_events": prior_events + [event],
    }
