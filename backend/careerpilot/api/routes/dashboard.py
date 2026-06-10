"""Dashboard endpoint — single call returns everything the frontend dashboard needs."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException

from careerpilot.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(user: dict = Depends(get_current_user)):
    """
    Returns:
      - upcoming_interviews : future interviews ordered by date (calendar)
      - past_interviews     : last 20 completed/failed interviews with full detail
      - today_log           : today's daily_log entry or null
      - recent_logs         : last 30 days of daily_log (activity chart + history)
      - recent_checkins     : last 14 check-ins (mood, energy, wins, blockers)
      - today_plan          : today's plan + tasks
      - active_goal         : full latest goal plan (all milestones, targets, mode)
      - skill_map           : scored talent_map for skills dashboard card
      - tracking_skills     : self-reported / intake skills
      - snapshot            : days_since, days_left, phase, open_tasks, mood, energy
    """
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        today = date.today().isoformat()
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()

        # ── Upcoming interviews (calendar) ────────────────────────────────────
        upcoming_interviews = (
            sb.table("interviews")
            .select("*")
            .eq("user_id", user_id)
            .gte("date", today)
            .order("date", desc=False)
            .execute()
        ).data or []

        # ── Past interviews (full detail) ─────────────────────────────────────
        past_interviews = (
            sb.table("interviews")
            .select("*")
            .eq("user_id", user_id)
            .lt("date", today)
            .order("date", desc=True)
            .limit(20)
            .execute()
        ).data or []

        # ── Today's log ───────────────────────────────────────────────────────
        today_log_rows = (
            sb.table("daily_log")
            .select("*")
            .eq("user_id", user_id)
            .eq("date", today)
            .limit(1)
            .execute()
        ).data
        today_log = today_log_rows[0] if today_log_rows else None

        # ── Last 30 days activity ─────────────────────────────────────────────
        recent_logs = (
            sb.table("daily_log")
            .select("*")
            .eq("user_id", user_id)
            .gte("date", thirty_days_ago)
            .order("date", desc=False)
            .execute()
        ).data or []

        # ── Last 14 check-ins ─────────────────────────────────────────────────
        recent_checkins = (
            sb.table("checkins")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(14)
            .execute()
        ).data or []

        # ── Today's plan + tasks ──────────────────────────────────────────────
        today_plan = None
        plan_row = (
            sb.table("plans")
            .select("id, date, coach_note, plan_json, schedule, priority_mode")
            .eq("user_id", user_id)
            .eq("date", today)
            .limit(1)
            .execute()
        ).data
        if plan_row:
            p = plan_row[0]
            tasks = (
                sb.table("plan_tasks")
                .select("*")
                .eq("plan_id", p["id"])
                .order("priority", desc=False)
                .execute()
            ).data or []
            today_plan = {
                "plan_id": p["id"],
                "date": today,
                "coach_note": p.get("coach_note", ""),
                "priority_mode": p.get("priority_mode", "standard"),
                "schedule": p.get("schedule") or {},
                "tasks": tasks,
                **(p.get("plan_json") or {}),
            }

        # ── Full latest goal plan ─────────────────────────────────────────────
        active_goal = None
        goal_row = (
            sb.table("goal_plan")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data
        if goal_row:
            active_goal = goal_row[0]

        # ── User profile ──────────────────────────────────────────────────────
        profile = (
            sb.table("users")
            .select("search_start_date, runway_weeks, open_tasks, phase, "
                    "talent_map, tracking_skills, role, leetcode_level, intake_complete")
            .eq("id", user_id)
            .single()
            .execute()
        ).data or {}

        days_since = None
        if profile.get("search_start_date"):
            days_since = (date.today() - date.fromisoformat(profile["search_start_date"])).days

        deadline_candidates = []
        if profile.get("runway_weeks") is not None:
            deadline_candidates.append(profile["runway_weeks"] * 7)
        days_left = min(deadline_candidates) if deadline_candidates else None

        latest_checkin = recent_checkins[0] if recent_checkins else {}

        return {
            "upcoming_interviews": upcoming_interviews,
            "past_interviews": past_interviews,
            "today_log": today_log,
            "recent_logs": recent_logs,
            "recent_checkins": recent_checkins,
            "today_plan": today_plan,
            "active_goal": active_goal,
            "skill_map": profile.get("talent_map"),
            "tracking_skills": profile.get("tracking_skills"),
            "snapshot": {
                "days_since": days_since,
                "days_left": days_left,
                "phase": profile.get("phase"),
                "open_tasks": profile.get("open_tasks"),
                "role": profile.get("role"),
                "leetcode_level": profile.get("leetcode_level"),
                "intake_complete": profile.get("intake_complete"),
                "mood_score": latest_checkin.get("mood_score"),
                "energy_score": latest_checkin.get("energy_score"),
                "last_checkin_at": latest_checkin.get("created_at"),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
