import json as _json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from crisiscoach.api.routes.auth import get_current_user

router = APIRouter()

class IntakePayload(BaseModel):
    role: str
    offer_timeline: str
    leetcode_level: Optional[str] = None
    resume_text: Optional[str] = None


@router.post("/intake")
async def submit_intake(payload: IntakePayload, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    updates: dict = {
        "role": payload.role,
        "offer_timeline": payload.offer_timeline,
        "intake_complete": True,
        "phase": "goal_setup",
    }

    if payload.leetcode_level:
        updates["leetcode_level"] = payload.leetcode_level

    if payload.resume_text and payload.resume_text.strip():
        updates["resume_text"] = payload.resume_text.strip()

    try:
        from crisiscoach.db.supabase import get_client
        get_client().table("users").upsert({"id": user_id, **updates}).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


FIELD_OPTIONS: dict[str, list[dict]] = {
    "role": [
        {"value": "SWE", "label": "Software Engineer"},
        {"value": "MLE", "label": "ML Engineer"},
        {"value": "AI Engineer", "label": "AI Engineer"},
        {"value": "Data Engineer", "label": "Data Engineer"},
        {"value": "Other", "label": "Other"},
    ],
    "offer_timeline": [
        {"value": "1_2_months", "label": "ASAP — within 2 months"},
        {"value": "3_months", "label": "~3 months"},
        {"value": "3_6_months", "label": "3–6 months"},
        {"value": "6_plus", "label": "6+ months, no rush"},
    ],
    "leetcode_level": [
        {"value": "cant_do_two_sum", "label": "Just getting started"},
        {"value": "shaky_mediums", "label": "Shaky on mediums"},
        {"value": "comfortable_mediums", "label": "Solid on mediums"},
        {"value": "can_do_hards", "label": "Can do hards"},
    ],
}

FIELD_LABEL: dict[str, str] = {
    "role": "What kind of engineer are you?",
    "offer_timeline": "What's your timeline to land an offer?",
    "leetcode_level": "Where's your coding interview prep right now?",
}


class IntakeMessage(BaseModel):
    role: str
    content: str


class IntakeStreamRequest(BaseModel):
    messages: list[IntakeMessage] = []
    collected_fields: dict = {}


@router.post("/intake/stream")
async def intake_stream(request: IntakeStreamRequest, user: dict = Depends(get_current_user)):
    """Streams structured intake steps driven by the intake agent."""
    from crisiscoach.agents.runtime import intake as intake_agent

    user_id = user.get("sub", "")

    lc_messages = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in request.messages
    ]

    state: dict = {
        "messages": lc_messages,
        "user_id": user_id,
        "intent": "intake",
        "agent": "intake",
        "days_since": None,
        "days_left": None,
        "mood_score": None,
        "energy_score": None,
        "open_tasks": None,
        "resume_text": None,
        "linkedin_text": None,
        "tracking_summary": None,
        "tracking_skills": None,
        "talent_map": None,
        "intake_complete": False,
        "phase": "intake",
        "response": "",
        "sources": [],
        "chips": [],
        "agent_events": [],
        "leetcode_level": None,
        "role": None,
        "collected_fields": request.collected_fields,
    }

    async def event_gen():
        ts = datetime.now(timezone.utc).isoformat()
        yield f"data: {_json.dumps({'type': 'agent_event', 'agent': 'intake', 'display_name': 'Intake Specialist', 'reason': 'Collecting your profile', 'timestamp': ts})}\n\n"

        try:
            result = await intake_agent.run(state)
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        field_key = result.get("field_key")
        structured_options = FIELD_OPTIONS.get(field_key, []) if field_key else []
        step = {
            "type": "step",
            "reply": result.get("response", ""),
            "field_key": field_key,
            "question": FIELD_LABEL.get(field_key, "") if field_key else "",
            "options": structured_options,
            "intake_complete": result.get("intake_complete", False),
            # Only use LLM chips when there are no structured options (e.g. goal confirmation phase)
            "chips": [] if structured_options else result.get("chips", []),
        }
        yield f"data: {_json.dumps(step)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/intake/status")
async def get_intake_status(user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        from crisiscoach.db.supabase import get_client
        rows = (
            get_client()
            .table("users")
            .select("intake_complete, phase")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not rows.data:
            return {"intake_complete": False, "phase": "intake"}
        data = rows.data[0]
        return {
            "intake_complete": bool(data.get("intake_complete")),
            "phase": data.get("phase", "intake"),
        }
    except Exception:
        return {"intake_complete": False, "phase": "intake"}
