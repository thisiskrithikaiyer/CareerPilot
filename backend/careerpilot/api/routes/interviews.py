from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from careerpilot.api.routes.auth import get_current_user

router = APIRouter()

STAGES = Literal["phone_screen", "technical", "system_design", "behavioral", "onsite", "final"]
HOW_CONTACTED = Literal["linkedin", "referral", "job_board", "cold_apply", "recruiter", "other"]
STATUS = Literal["pass", "fail", "pending"]


class InterviewCreate(BaseModel):
    company: str
    role: str | None = None
    stage: STAGES
    date: str                          # ISO date string
    how_contacted: HOW_CONTACTED | None = None
    topics: list[str] = []            # skill topics covered e.g. ["dynamic programming", "system design"]
    questions_asked: list[str] = []
    what_went_wrong: str | None = None
    notes: str | None = None
    status: STATUS = "pending"


class InterviewUpdate(BaseModel):
    status: STATUS | None = None
    what_went_wrong: str | None = None
    notes: str | None = None
    topics: list[str] | None = None
    questions_asked: list[str] | None = None


@router.post("/interviews", status_code=201)
async def log_interview(body: InterviewCreate, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        result = sb.table("interviews").insert({
            "user_id": user_id,
            "company": body.company,
            "role": body.role,
            "stage": body.stage,
            "date": body.date,
            "how_contacted": body.how_contacted,
            "topics": body.topics,
            "questions_asked": body.questions_asked,
            "what_went_wrong": body.what_went_wrong,
            "notes": body.notes,
            "status": body.status,
        }).execute()

        # Re-score skills in background — new interview data is the highest-signal input
        import asyncio
        from careerpilot.agents.background.talent_mapper import map_talent
        asyncio.get_event_loop().create_task(map_talent(user_id))

        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/interviews/{interview_id}")
async def update_interview(interview_id: str, body: InterviewUpdate, user: dict = Depends(get_current_user)):
    """Update outcome after the interview — flip pending → pass/fail, add notes."""
    user_id = user.get("sub", "")
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            return {"ok": True}
        sb.table("interviews").update(updates).eq("id", interview_id).eq("user_id", user_id).execute()

        # Re-score if outcome changed
        if body.status in ("pass", "fail"):
            import asyncio
            from careerpilot.agents.background.talent_mapper import map_talent
            asyncio.get_event_loop().create_task(map_talent(user_id))

        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interviews")
async def get_interviews(limit: int = 20, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "")
    try:
        from careerpilot.db.supabase import get_client
        rows = (
            get_client()
            .table("interviews")
            .select("*")
            .eq("user_id", user_id)
            .order("date", desc=True)
            .limit(limit)
            .execute()
        ).data or []
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
