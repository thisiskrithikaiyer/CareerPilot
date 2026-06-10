"""Mental health check agent — crisis-aware, empathetic, resource-linking."""
import asyncio
from langchain_core.messages import HumanMessage
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.prompts.loader import load_prompt

CRISIS_KEYWORDS = {"suicid", "end my life", "don't want to be here", "kill myself", "self-harm"}

SAFETY_RESPONSE = (
    "Please reach out to the 988 Suicide & Crisis Lifeline — call or text 988. "
    "They're available 24/7 and you don't have to be in immediate danger to call. "
    "If you're in immediate danger, call 911."
)


def _is_crisis(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CRISIS_KEYWORDS)


def _rebuild_plan_tomorrow(user_id: str) -> None:
    """Fire-and-forget: rebuild tomorrow's plan so burnout_recovery mode kicks in."""
    from datetime import date, timedelta
    from careerpilot.agents.background.daily_check import build_daily_plan
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    try:
        asyncio.get_running_loop().create_task(build_daily_plan(user_id, for_date=tomorrow))
    except Exception as e:
        print(f"[MENTAL_HEALTH] plan rebuild failed: {e}")


async def run(state: State) -> dict:
    last_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    content = last_msg.content if last_msg else ""

    if _is_crisis(content):
        return {"response": SAFETY_RESPONSE, "sources": ["https://988lifeline.org"]}

    base = load_prompt("mental_health.txt")
    mood = state.get("mood_score")
    mood_context = f"\nUser's last logged mood: {mood}/10." if mood else ""
    system = base + mood_context

    history = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state["messages"]
    ]
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": system}, *history],
    )
    reply = resp.choices[0].message.content.strip()
    reply += "\n\nI've also lightened tomorrow's plan — rest is part of the search."

    user_id = state.get("user_id")
    if user_id:
        _rebuild_plan_tomorrow(user_id)

    return {"response": reply, "sources": [], "needs_plan_refresh": True}
