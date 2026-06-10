"""Interview prep agent — weekly prep plan based on target roles and interview stage."""
import json
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL


async def generate_prep_plan(user_id: str) -> dict:
    from careerpilot.db.supabase import get_client
    sb = get_client()

    profile = (
        sb.table("users")
        .select("talent_map, active_pipeline, interview_stage")
        .eq("id", user_id)
        .single()
        .execute()
    )
    data = profile.data or {}

    context = json.dumps({
        "talent_map": data.get("talent_map", {}),
        "active_pipeline": data.get("active_pipeline", []),
        "interview_stage": data.get("interview_stage", "initial_screen"),
    })

    system = (
        "You are an interview coach. Given the user's profile, generate a focused weekly prep plan. "
        "Output JSON only: "
        '{"focus_area": "...", "daily_tasks": [{"day": "Mon", "task": "...", "duration_mins": <int>}], '
        '"mock_question": "...", "resource": "..."}. '
        "Be specific to their target role. No generic tips."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=768,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": context},
        ],
    )
    plan = json.loads(resp.choices[0].message.content)

    sb.table("interview_prep_plans").insert({
        "user_id": user_id,
        "plan": plan,
    }).execute()

    return plan
