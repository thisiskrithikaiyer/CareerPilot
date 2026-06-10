"""Severance agent — parses severance package on onboarding and tracks declining balance."""
import json
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL


async def parse_severance(user_id: str, raw_text: str) -> dict:
    """
    Given raw severance letter text, extract key terms via LLM and persist.
    Called at onboarding when user uploads or pastes their severance agreement.
    """
    system = (
        "Extract severance details from the provided text. "
        'Output JSON only: {"weeks_pay": <int>, "lump_sum": <float|null>, '
        '"cobra_covered_months": <int>, "non_compete_months": <int|null>, '
        '"signing_deadline_days": <int|null>, "equity_cliff_preserved": <bool>}. '
        "Use null for missing fields."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=256,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": raw_text[:4000]},
        ],
    )
    parsed = json.loads(resp.choices[0].message.content)

    from careerpilot.db.supabase import get_client
    sb = get_client()
    sb.table("users").update({
        "severance_weeks": parsed.get("weeks_pay"),
        "severance_lump_sum": parsed.get("lump_sum"),
        "cobra_months": parsed.get("cobra_covered_months"),
        "non_compete_months": parsed.get("non_compete_months"),
    }).eq("id", user_id).execute()

    return parsed


async def update_severance_balance(user_id: str) -> dict:
    """Weekly: decrement remaining severance weeks and recalc balance."""
    from careerpilot.db.supabase import get_client
    sb = get_client()

    profile = (
        sb.table("users")
        .select("severance_weeks, severance_weeks_remaining, last_paycheck_amount")
        .eq("id", user_id)
        .single()
        .execute()
    )
    data = profile.data or {}
    remaining = int(data.get("severance_weeks_remaining") or data.get("severance_weeks") or 0)

    if remaining <= 0:
        return {"done": True}

    remaining -= 1
    weekly_amount = float(data.get("last_paycheck_amount") or 0)
    sb.table("users").update({
        "severance_weeks_remaining": remaining,
        "severance_remaining": remaining * weekly_amount,
    }).eq("id", user_id).execute()

    return {"weeks_remaining": remaining, "balance": remaining * weekly_amount}
