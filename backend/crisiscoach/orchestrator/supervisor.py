"""
Supervisor agent — the central brain of CrisisCoach.
Reads phase, conversation history, and user context to decide which agent runs next.
Replaces the rule-based router with an LLM that reasons about handoffs.
"""
import json
from datetime import date
from langchain_core.messages import HumanMessage
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL
from crisiscoach.orchestrator.state import CrisisCoachState
from crisiscoach.orchestrator.state_prompt import state_to_prompt

AGENTS = {
    "intake": (
        "Runs when phase is intake. Handles only new users. Collects all the information from the user, "
        "Once all required information is registered change phase=goal_setup."
    ),
    "goal_planner": (
        "Builds or revises the job search strategy for the deadline. Runs when phase=goal_setup "
        "or when user explicitly wants to revisit their plan."
    ),
    "checkin": (
        "User is logging how today went: mood, energy, wins, blockers, prep done, applications sent, interviews completed."
    ),
    "accountability": (
        "User wants to review planned vs actual, be held to commitments, or is showing drift: "
        "missed days, low motivation, spiraling, or wasting time."
    ),
    "mental_health": (
        "User is expressing extreme distress, burnout, hopelessness, or crisis signals like suicidal ideation or self-harm. "
        "ALWAYS takes priority — route here if ANY distress signal is present."
    ),
    "chat": (
        "General questions or conversation that don't fit any other agent."
    ),
}

GOAL_SETUP_PHASES = {"goal_setup", "goal_planner"}
ROUTABLE_AGENTS = set(AGENTS)

MENTAL_HEALTH_SIGNALS = {
    "want to die", "kill myself", "end it", "can't go on", "hopeless",
    "suicidal", "no point", "give up", "breaking down",
    "can't do this anymore", "i'm done", "falling apart", "can't handle this",
    "panic attack", "having a breakdown", "not okay", "losing it",
}

_SUPERVISOR_SYSTEM = """You are the supervisor of CrisisCoach AI — a job-loss coaching app.
Your only job is to decide which specialist agent should handle the user's current message.

Today's date: {today}

Available agents:
{agents}

Phase rules (HARD — never break these):
- phase=intake → ONLY route to "intake". No exceptions except mental_health crisis.
- phase=goal_setup → ONLY route to "goal_planner". No exceptions except mental_health crisis.
- phase=goal_planner → treat as legacy goal_setup and route to "goal_planner".
- phase=active → route freely based on the user's message.

Mental health override: If the user shows ANY crisis signal (hopelessness, self-harm, suicidal ideation), ALWAYS route to "mental_health" regardless of phase.

User context:
{context}

Output a single JSON object. No explanation.
{{"agent": "<agent_name>", "reason": "<one line why>"}}
"""




def _is_crisis(text: str) -> bool:
    return any(signal in text.lower() for signal in MENTAL_HEALTH_SIGNALS)


def decide(state: CrisisCoachState) -> tuple[str, str]:
    """Return (agent_name, reason) for the routing decision."""
    phase = state.get("phase", "intake")

    last_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    if last_msg is None:
        if phase == "intake":
            return ("intake", "No messages yet")
        if phase in GOAL_SETUP_PHASES:
            return ("goal_planner", "Phase locked: building your goal strategy")
        return ("chat", "No messages yet")

    text = last_msg.content.strip()

    # Hard crisis override
    if _is_crisis(text):
        print("[SUPERVISOR] Crisis signal detected → mental_health")
        return ("mental_health", "Crisis signal detected in user message")

    # Hard phase locks — no LLM needed
    if phase == "intake":
        return ("intake", "Phase locked: collecting onboarding information")
    if phase in GOAL_SETUP_PHASES:
        return ("goal_planner", "Phase locked: building your goal strategy")

    # phase=active — ask the LLM supervisor
    agents_desc = "\n".join(f'- "{k}": {v}' for k, v in AGENTS.items())
    context_snippet = state_to_prompt(state)

    # Last 4 messages for context
    recent = state["messages"][-4:]
    convo = "\n".join(
        f"{'USER' if isinstance(m, HumanMessage) else 'COACH'}: {m.content[:200]}"
        for m in recent
    )

    try:
        resp = groq_complete(
            model=GROQ_MODEL,
            max_tokens=80,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": _SUPERVISOR_SYSTEM.format(
                        today=date.today().isoformat(),
                        agents=agents_desc,
                        context=context_snippet,
                    ),
                },
                {
                    "role": "user",
                    "content": f"Recent conversation:\n{convo}\n\nLatest user message: {text}",
                },
            ],
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw)
        agent = data.get("agent", "chat")
        reason = data.get("reason", "LLM routing decision")
        result = agent if agent in ROUTABLE_AGENTS else "chat"
        print(f"[SUPERVISOR] phase={phase} | agent={result} | reason={reason}")
        return (result, reason)
    except Exception as e:
        print(f"[SUPERVISOR] LLM failed, defaulting to chat: {e}")
        return ("chat", "Fallback: LLM routing unavailable")
