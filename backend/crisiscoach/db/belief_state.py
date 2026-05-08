"""
Belief state — the system's evolving model of the user's job search reality.

Written by: target_recalibrator (on commitment + weekly)
Read by:    goal_planner, daily_check (via signals)

Stored as JSONB in users.belief_state. All writes are non-blocking.
"""
from __future__ import annotations
from datetime import date

_DEFAULT: dict = {
    "estimated_screen_rate": 0.10,
    "estimated_pass_rate": 0.50,
    "estimated_rounds": 5,
    "estimated_lc_goal": 75,
    "experience_band": None,          # junior | mid | senior | staff_plus
    "resume_score": None,
    "primary_gap": None,              # resume | volume | technical_lc | technical_sd | behavioral | networking | burnout | on_track
    "gap_confidence": "low",          # low | medium | high
    "diagnosis": None,                # 1-sentence diagnosis from LLM
    "top_actions": [],                # 2 specific things to fix today
    "data_points": 0,                 # total apps + interviews seen so far
    "last_updated": None,
}


def read(user_id: str, sb) -> dict:
    try:
        row = (
            sb.table("users")
            .select("belief_state")
            .eq("id", user_id)
            .single()
            .execute()
        ).data or {}
        stored = row.get("belief_state") or {}
        return {**_DEFAULT, **stored}
    except Exception:
        return dict(_DEFAULT)


def write(user_id: str, updates: dict, sb) -> None:
    try:
        current = read(user_id, sb)
        merged = {**current, **updates, "last_updated": date.today().isoformat()}
        sb.table("users").update({"belief_state": merged}).eq("id", user_id).execute()
    except Exception as e:
        print(f"[BELIEF_STATE] write failed: {e}")


def bayesian_update(prior: float, observed: float, n_obs: int) -> float:
    """
    Blend prior and observed rate weighted by data volume.
    Prior dominates until n_obs reaches 50; observed dominates at 50+.
    """
    alpha = min(0.8, n_obs / 50)
    return round((1 - alpha) * prior + alpha * observed, 4)
