from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from careerpilot.api.routes.auth import get_current_user
from careerpilot.db.schemas.checkin import CheckinCreate, CheckinOut

router = APIRouter()


class CheckinRequest(BaseModel):
    mood_score: int = Field(..., ge=1, le=10, description="1 = exhausted, 10 = energized")
    energy_score: int = Field(..., ge=1, le=10)
    wins: list[str] = []
    blockers: list[str] = []
    notes: str = ""


class CheckinResponse(BaseModel):
    id: str
    created_at: str
    mood_score: int
    energy_score: int
    coach_response: str


@router.post("/checkin", response_model=CheckinResponse)
async def submit_checkin(body: CheckinRequest, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "")
    try:
        from careerpilot.db.supabase import get_client
        from careerpilot.agents.runtime.daily_tracker import generate_checkin_response

        sb = get_client()
        row = CheckinCreate(
            user_id=user_id,
            mood_score=body.mood_score,
            energy_score=body.energy_score,
            wins=body.wins,
            blockers=body.blockers,
            notes=body.notes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        result = sb.table("checkins").insert(row.model_dump()).execute()
        saved = result.data[0]

        coach_response = await generate_checkin_response(
            mood_score=body.mood_score,
            energy_score=body.energy_score,
            wins=body.wins,
            blockers=body.blockers,
        )
        return CheckinResponse(
            id=saved["id"],
            created_at=saved["created_at"],
            mood_score=saved["mood_score"],
            energy_score=saved["energy_score"],
            coach_response=coach_response,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkin/history")
async def get_checkin_history(limit: int = 7, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "")
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        result = (
            sb.table("checkins")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
