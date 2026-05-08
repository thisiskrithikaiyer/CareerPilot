from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from crisiscoach.api.routes.auth import get_current_user

router = APIRouter()

# Supabase migration — run this SQL to add the new columns:
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS dsa_problems INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS other_prep TEXT DEFAULT '';
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS system_design_topic TEXT DEFAULT '';
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS applications_sent INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS networking_sent INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS coffee_chat INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS called_for_calls INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS oa_pending INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS recruiter_screens INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS technical_rounds INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS final_rounds INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS mocks_done INT DEFAULT 0;
# ALTER TABLE daily_log ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT '';


class DailyLogRequest(BaseModel):
    date: Optional[str] = None
    # Core tracking
    dsa_problems: int = 0
    other_prep: str = ""
    system_design_topic: str = ""
    applications_sent: int = 0
    networking_sent: int = 0
    coffee_chat: int = 0
    called_for_calls: int = 0
    oa_pending: int = 0
    recruiter_screens: int = 0
    technical_rounds: int = 0
    final_rounds: int = 0
    mocks_done: int = 0
    notes: str = ""
    # Legacy fields kept for backward compat
    apps_done: int = 0
    networking_done: int = 0
    interviews_attended: int = 0
    leetcode_done: int = 0
    system_design_done: int = 0


@router.post("/daily-log")
async def upsert_daily_log(body: DailyLogRequest, user: dict = Depends(get_current_user)):
    """Upsert today's activity log. One row per user per day."""
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    log_date = body.date or date.today().isoformat()

    try:
        from crisiscoach.db.supabase import get_client
        sb = get_client()
        sb.table("daily_log").upsert(
            {
                "user_id": user_id,
                "date": log_date,
                # New fields
                "dsa_problems": body.dsa_problems,
                "other_prep": body.other_prep,
                "system_design_topic": body.system_design_topic,
                "applications_sent": body.applications_sent,
                "networking_sent": body.networking_sent,
                "coffee_chat": body.coffee_chat,
                "called_for_calls": body.called_for_calls,
                "oa_pending": body.oa_pending,
                "recruiter_screens": body.recruiter_screens,
                "technical_rounds": body.technical_rounds,
                "final_rounds": body.final_rounds,
                "mocks_done": body.mocks_done,
                "notes": body.notes,
                # Legacy
                "apps_done": body.apps_done or body.applications_sent,
                "networking_done": body.networking_done or body.networking_sent,
                "interviews_attended": body.interviews_attended,
                "leetcode_done": body.leetcode_done or body.dsa_problems,
                "system_design_done": body.system_design_done,
            },
            on_conflict="user_id,date",
        ).execute()
        return {"ok": True, "date": log_date}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-log")
async def get_daily_log(days: int = 90, user: dict = Depends(get_current_user)):
    """Return the last N days of activity logs."""
    user_id = user.get("sub", "")
    try:
        from crisiscoach.db.supabase import get_client
        rows = (
            get_client()
            .table("daily_log")
            .select("*")
            .eq("user_id", user_id)
            .order("date", desc=True)
            .limit(days)
            .execute()
        ).data or []
        return list(reversed(rows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
