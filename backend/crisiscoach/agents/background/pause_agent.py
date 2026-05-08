"""Pause agent — nightly burnout signal check. Flags users who need a rest day."""
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL

BURNOUT_THRESHOLD_MOOD = 4       # avg mood below this triggers flag
BURNOUT_THRESHOLD_DAYS = 3       # consecutive low-mood days


async def run_for_user(user_id: str) -> dict:
    """Check the last N check-ins and flag burnout risk. Returns recommended action."""
    from crisiscoach.db.supabase import get_client
    sb = get_client()

    rows = (
        sb.table("checkins")
        .select("mood_score, energy_score, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(BURNOUT_THRESHOLD_DAYS)
        .execute()
    )
    checkins = rows.data
    if len(checkins) < BURNOUT_THRESHOLD_DAYS:
        return {"burnout_flag": False, "reason": "insufficient_data"}

    avg_mood = sum(c["mood_score"] for c in checkins) / len(checkins)
    avg_energy = sum(c["energy_score"] for c in checkins) / len(checkins)

    if avg_mood <= BURNOUT_THRESHOLD_MOOD:
        recommendation = _generate_pause_recommendation(avg_mood, avg_energy)
        sb.table("users").update({"burnout_flag": True}).eq("id", user_id).execute()
        return {"burnout_flag": True, "avg_mood": avg_mood, "recommendation": recommendation}

    sb.table("users").update({"burnout_flag": False}).eq("id", user_id).execute()
    return {"burnout_flag": False, "avg_mood": avg_mood}


def _generate_pause_recommendation(avg_mood: float, avg_energy: float) -> str:
    prompt = (
        f"User has averaged a mood of {avg_mood:.1f}/10 and energy of {avg_energy:.1f}/10 "
        f"over the last {BURNOUT_THRESHOLD_DAYS} days during their job search. "
        "Write a brief (2-3 sentence) compassionate message telling them it's okay to take a rest day "
        "and suggesting one restorative activity. Be direct, not saccharine."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content
