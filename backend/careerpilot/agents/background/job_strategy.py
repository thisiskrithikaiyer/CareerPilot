"""Job strategy agent — weekly market data refresh and pipeline recommendations."""
import json
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL


def _experience_tier(years: int | None) -> str:
    if years is None:
        return "mid-level"
    if years <= 2:
        return "entry-level"
    if years <= 6:
        return "mid-level"
    if years <= 12:
        return "senior"
    return "staff/principal"


async def refresh_strategy(user_id: str) -> dict:
    from careerpilot.db.supabase import get_client
    from careerpilot.db.vector_store import query_collection

    sb = get_client()
    profile = (
        sb.table("users")
        .select("talent_map, runway_weeks, resume_text, years_experience")
        .eq("id", user_id)
        .single()
        .execute()
    )
    data = profile.data or {}
    talent_map = data.get("talent_map", {})

    target_roles = talent_map.get("target_roles", [])
    if not target_roles:
        return {"skipped": True, "reason": "no_target_roles"}

    years_exp = data.get("years_experience") or talent_map.get("years_experience")
    tier = _experience_tier(years_exp)
    seniority = talent_map.get("seniority", tier)
    top_skills = talent_map.get("top_skills", [])
    industries = talent_map.get("industries", [])

    # Build an experience-aware query so the vector store returns relevant tier chunks
    role_str = ", ".join(target_roles[:3])
    skill_str = ", ".join(top_skills[:4]) if top_skills else ""
    query = (
        f"{tier} job search strategy for {role_str}"
        + (f" with skills in {skill_str}" if skill_str else "")
    )
    market_chunks = query_collection("job_strategy", query, n_results=6)

    # Also pull a pipeline/timing chunk specific to their runway
    runway = data.get("runway_weeks")
    if runway is not None:
        timing_query = f"runway {'urgent' if runway < 8 else 'patient'} job search timeline"
        market_chunks += query_collection("job_strategy", timing_query, n_results=2)

    context = json.dumps(
        {
            "experience_tier": tier,
            "seniority": seniority,
            "years_experience": years_exp,
            "target_roles": target_roles,
            "top_skills": top_skills,
            "industries": industries,
            "runway_weeks": runway,
            "market_intel": market_chunks,
        },
        default=str,
    )

    system = (
        "You are a job strategy advisor. Given the user's experience level, skills, and market intel, "
        "output a personalized weekly strategy recommendation as JSON only — no markdown, no explanation:\n"
        '{"priority_roles": [...], "companies_to_target": [...], "outreach_goal": <int>, '
        '"experience_based_insight": "...", "strategic_insight": "...", "avoid": "..."}.\n'
        "Tailor the advice to the user's specific experience tier and background. "
        "Be concrete and actionable — no motivational filler. "
        "experience_based_insight must be specific to their seniority level and skills."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=600,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": context},
        ],
    )
    strategy = json.loads(resp.choices[0].message.content)
    sb.table("job_strategies").upsert(
        {"user_id": user_id, "strategy": strategy},
        on_conflict="user_id",
    ).execute()

    return strategy
