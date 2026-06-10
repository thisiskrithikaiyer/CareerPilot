import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from careerpilot.api.routes.auth import get_current_user

router = APIRouter()


class ResumeUpload(BaseModel):
    text: str


class LinkedInUpload(BaseModel):
    text: str


@router.post("/resume")
async def upload_resume(body: ResumeUpload, user: dict = Depends(get_current_user)):
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        sb.table("users").update({"resume_text": body.text}).eq("id", user_id).execute()
        from careerpilot.agents.background.talent_mapper import map_talent
        asyncio.get_event_loop().create_task(map_talent(user_id, resume_text=body.text))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/linkedin")
async def upload_linkedin(body: LinkedInUpload, user: dict = Depends(get_current_user)):
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        sb.table("users").update({"linkedin_text": body.text}).eq("id", user_id).execute()
        from careerpilot.agents.background.talent_mapper import map_talent
        asyncio.get_event_loop().create_task(map_talent(user_id, linkedin_summary=body.text))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
