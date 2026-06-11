from langchain_core.messages import HumanMessage
"""Daily tracker agent — processes check-in messages, PERSISTS progress, and
closes plan tasks. Every substantive check-in also triggers a proactive rebuild
of tomorrow's plan so the coach preps next-day tasks from what was actually done."""
import asyncio

from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.agents.runtime.progress_actions import (
    extract_progress,
    has_progress,
    apply_progress,
    close_plan_tasks,
    open_task_labels,
)


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


def _prep_tomorrow(user_id: str) -> None:
    """Proactively rebuild tomorrow's plan from what was completed today."""
    from datetime import date, timedelta
    from careerpilot.agents.background.daily_check import build_daily_plan

    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    async def _build():
        try:
            await build_daily_plan(user_id, for_date=tomorrow)
            print(f"[DAILY_TRACKER] Proactively prepped tomorrow's plan ({tomorrow}) for {user_id}")
        except Exception as e:
            print(f"[DAILY_TRACKER] Tomorrow prep failed: {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_build())
        else:
            loop.run_until_complete(_build())
    except Exception as e:
        print(f"[DAILY_TRACKER] Could not schedule tomorrow prep: {e}")


async def run(state: State) -> dict:
    last_msg = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
    )
    content = last_msg.content if last_msg else ""
    user_id = state.get("user_id")

    saved_summary = None
    closed_tasks: list[str] = []
    remaining: list[str] = []
    progress = None

    if user_id and _has_progress_content(content):
        # 1. Extract structured progress and persist it — this is the write path,
        #    not just a chat reply. Failures degrade to a plain coaching reply.
        progress = extract_progress(content)
        try:
            if progress.get("close_tasks"):
                closed_tasks = close_plan_tasks(user_id, progress["close_tasks"])
            if has_progress(progress):
                saved_summary = apply_progress(user_id, progress)
            remaining = open_task_labels(user_id)
        except Exception as e:
            print(f"[DAILY_TRACKER] Persistence failed: {e}")

        # 2. Proactive next-day prep — the key behavior: once today's progress is
        #    logged, rebuild tomorrow's plan around what was actually completed.
        if saved_summary or closed_tasks:
            _prep_tomorrow(user_id)

    if _has_progress_content(content):
        facts = []
        if saved_summary and saved_summary.get("log_updates"):
            updates = ", ".join(f"{k.replace('_', ' ')}={v}" for k, v in saved_summary["log_updates"].items())
            facts.append(f"Saved to today's tracker: {updates}.")
        if saved_summary and saved_summary.get("checkin_saved"):
            facts.append("Check-in (mood/energy/wins/blockers) saved.")
        if closed_tasks:
            facts.append("Closed plan tasks: " + "; ".join(closed_tasks) + ".")
        if progress and progress.get("close_tasks") and not closed_tasks:
            facts.append("No matching open task was found to close — tell the user which tasks are still open.")
        if facts and remaining:
            facts.append("Still open on today's plan: " + "; ".join(remaining) + ".")
        if saved_summary or closed_tasks:
            facts.append("Tomorrow's plan is being re-prepped around this progress.")

        if facts:
            facts_text = "\n".join(f"- {f}" for f in facts)
            system = (
                "You are CrisisCoach — a direct, no-fluff career coach for tech professionals in career transition. "
                "The user shared what they did today and the system ALREADY saved it. "
                "Confirm concretely what was logged/closed (use the system facts below — never invent numbers), "
                "acknowledge their progress by naming specifically what they did and why it matters, "
                "then give ONE targeted next step (prefer one of the still-open tasks). "
                "Do NOT ask for mood or energy scores — they already shared their update. "
                "BANNED PHRASES — never say: 'proud of you', 'amazing', 'incredible', 'fantastic', "
                "'keep your head up', 'stay positive', 'you've got this', 'great job', 'on a scale', 'rate your mood'. "
                "Under 150 words.\n\n"
                f"System facts (already done — report them accurately):\n{facts_text}"
            )
        else:
            # Nothing was persisted (no counts, no DB) — plain coaching reply.
            # Never mention the system, persistence, or logging mechanics.
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
    if user_id:
        try:
            from careerpilot.agents.background.talent_mapper import map_talent
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(map_talent(user_id))
            else:
                loop.run_until_complete(map_talent(user_id))
        except Exception as e:
            print(f"[DAILY_TRACKER] Background talent map failed: {e}")

    return {
        "response": resp.choices[0].message.content,
        "sources": [],
        "needs_plan_refresh": bool(closed_tasks or (saved_summary and saved_summary.get("log_updates"))),
    }
