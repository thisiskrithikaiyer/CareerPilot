"""
Supervisor agent — the central brain of CrisisCoach.
Reads phase, conversation history, and user context to decide which agent runs next.
Replaces the rule-based router with an LLM that reasons about handoffs.
"""
import json
from datetime import date
from langchain_core.messages import HumanMessage
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.orchestrator.state_prompt import state_to_prompt

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
        "User is reporting CONCRETE progress: prep done, applications sent, interviews completed, mood/energy numbers. "
        "ALSO handles task commands — 'close the X task', 'mark X done', 'finished X', 'completed X'. "
        "If the user is instead expressing drift, missed days, low motivation, or that they did nothing, "
        "prefer 'accountability' over 'checkin'. Likewise if a progress report centers on a rejection or "
        "setback they are processing emotionally (e.g. 'got rejected from the loop I was counting on'), "
        "prefer 'accountability'."
    ),
    "accountability": (
        "User wants to review planned vs actual, be held to commitments, or is showing drift: "
        "missed days, low motivation, spiraling, or wasting time."
    ),
    "mental_health": (
        "User is expressing extreme distress, burnout, hopelessness, or crisis signals like suicidal ideation or self-harm. "
        "ALWAYS takes priority — route here if ANY distress signal is present."
    ),
    "resume": (
        "User wants to improve, review, or tailor their resume — specific bullets, summary, ATS optimization, "
        "or an overall assessment. Route here when the focus is the resume document itself."
    ),
    "linkedin": (
        "User wants to optimize their LinkedIn profile — headline, About section, visibility, or "
        "recruiter-facing positioning. Route here when the focus is LinkedIn specifically."
    ),
    "mock_prep": (
        "User wants to practice interviewing — behavioral, technical coding, system design, or mixed. "
        "Route here when they ask for a mock interview, want to practice questions, or want answer feedback."
    ),
    "patterns": (
        "User wants to understand their behavioral patterns, recurring blockers, or consistency trends "
        "across check-ins and task completion. Route here when they ask about habits, patterns, or trends."
    ),
    "chat": (
        "General questions or conversation that don't fit any other agent."
    ),
}

GOAL_SETUP_PHASES = {"goal_setup", "goal_planner"}
ROUTABLE_AGENTS = set(AGENTS)

MENTAL_HEALTH_SIGNALS = {
    # Hard crisis
    "want to die", "kill myself", "end it", "can't go on", "hopeless",
    "suicidal", "no point", "give up", "breaking down",
    "can't do this anymore", "i'm done", "falling apart", "can't handle this",
    "panic attack", "having a breakdown", "not okay", "losing it",
    # Burnout / overwhelm — must catch these before any phase lock
    "can't do this", "need a break", "need break", "i give up",
    "overwhelmed", "exhausted", "burned out", "burning out",
    "too much", "breaking point", "can't cope", "too stressed",
    "can't take this", "done with this", "can't keep", "falling behind",
    "spiraling", "shutting down", "checked out",
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


def decide(state: State) -> tuple[str, str]:
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
