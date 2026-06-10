from langchain_core.messages import HumanMessage
"""Daily tracker agent — processes check-in messages and generates empathetic responses."""
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State


async def generate_checkin_response(
    mood_score: int,
    energy_score: int,
    wins: list[str],
    blockers: list[str],
) -> str:
    wins_text = "\n".join(f"- {w}" for w in wins) if wins else "None reported"
    blockers_text = "\n".join(f"- {b}" for b in blockers) if blockers else "None reported"
    user_msg = (
        f"Today's check-in:\n"
        f"Mood: {mood_score}/10, Energy: {energy_score}/10\n"
        f"Wins:\n{wins_text}\n"
        f"Blockers:\n{blockers_text}"
    )
    system = (
        "You are a direct, caring job-loss coach. Acknowledge the user's mood and energy honestly. "
        "Celebrate wins specifically — name WHAT they did, not generic praise. "
        "Name blockers and give one concrete suggestion. Be warm but brief (under 120 words). "
        "BANNED PHRASES — never say these: 'proud of you', 'amazing', 'incredible', 'fantastic', "
        "'keep your head up', 'stay positive', 'you've got this', 'great job'. "
        "Instead: name exactly what they did and why it matters."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=256,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
    )
    return resp.choices[0].message.content


def _has_progress_content(text: str) -> bool:
    """Return True if the message contains substantive progress info (not just a bare greeting)."""
    if not text:
        return False
    stripped = text.strip().lower()
    # Bare openers with no substance
    bare_openers = {"check in", "checkin", "check-in", "hi", "hello", "hey", "daily check-in", "daily checkin"}
    if stripped in bare_openers:
        return False
    # Must be long enough to contain real content
    return len(text.split()) >= 4


async def run(state: State) -> dict:
    last_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    content = last_msg.content if last_msg else ""

    if _has_progress_content(content):
        system = (
            "You are CrisisCoach — a direct, no-fluff career coach for tech professionals in career transition. "
            "The user has shared what they did today. Acknowledge their progress FIRST — name specifically "
            "what they did and why it matters (e.g. 'Two applications is concrete pipeline-building; "
            "the coffee chat is a warm lead worth following up'). Then give one targeted next step. "
            "Do NOT ask for mood or energy scores — they already shared their update. "
            "BANNED PHRASES — never say: 'proud of you', 'amazing', 'incredible', 'fantastic', "
            "'keep your head up', 'stay positive', 'you've got this', 'great job', 'on a scale', 'rate your mood'. "
            "Acknowledge wins by naming WHAT they did, not generic cheering. Under 150 words."
        )
    else:
        system = (
            "You are CrisisCoach — a direct, no-fluff career coach for tech professionals in career transition. "
            "The user wants to do their daily check-in but hasn't shared anything yet. "
            "Ask them to share: what they got done today, any blockers, and optionally their mood/energy (1-10). "
            "Keep it to one short question, not a form. "
            "BANNED PHRASES — never say: 'proud of you', 'amazing', 'incredible', 'fantastic', "
            "'keep your head up', 'stay positive', 'you've got this', 'great job'."
        )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
    )

    # Re-score skills in background after check-in — new wins/interview topics may have been logged
    user_id = state.get("user_id")
    if user_id:
        try:
            import asyncio
            from careerpilot.agents.background.talent_mapper import map_talent
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(map_talent(user_id))
            else:
                loop.run_until_complete(map_talent(user_id))
        except Exception as e:
            print(f"[DAILY_TRACKER] Background talent map failed: {e}")

    return {"response": resp.choices[0].message.content, "sources": []}
