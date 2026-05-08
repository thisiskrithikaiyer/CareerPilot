from langchain_core.messages import HumanMessage
"""Mental health check agent — crisis-aware, empathetic, resource-linking."""
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL
from crisiscoach.orchestrator.state import CrisisCoachState
from crisiscoach.prompts.loader import load_prompt

CRISIS_KEYWORDS = {"suicid", "end my life", "don't want to be here", "kill myself", "self-harm"}

SAFETY_RESPONSE = (
    "Please reach out to the 988 Suicide & Crisis Lifeline — call or text 988. "
    "They're available 24/7 and you don't have to be in immediate danger to call. "
    "If you're in immediate danger, call 911."
)


def _is_crisis(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CRISIS_KEYWORDS)


async def run(state: CrisisCoachState) -> dict:
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
    return {"response": resp.choices[0].message.content, "sources": []}
