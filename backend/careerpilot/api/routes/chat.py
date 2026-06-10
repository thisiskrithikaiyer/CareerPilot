import json as _json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from careerpilot.orchestrator import build_graph
from careerpilot.orchestrator.orchestrator import AGENT_MAP
from careerpilot.api.routes.auth import get_current_user

router = APIRouter()
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    user_id: str | None = None


AGENT_DISPLAY_NAMES = {
    "careerpilot.agents.runtime.intake":            "Intake Coach",
    "careerpilot.agents.runtime.goal_planner":      "Goal Strategist",
    "careerpilot.agents.runtime.daily_tracker":     "Daily Tracker",
    "careerpilot.agents.runtime.accountability":    "Accountability Coach",
    "careerpilot.agents.runtime.mental_health_check": "Wellness Coach",
}


def _extract_chips(raw: str) -> tuple[str, list[str]]:
    """Split LLM output into display text and chip options."""
    import json, re
    chips: list[str] = []
    text_lines: list[str] = []
    for line in raw.split("\n"):
        m = re.match(r"^CHIPS:\s*(\[.*\])\s*$", line.strip())
        if m:
            try:
                parsed = json.loads(m.group(1))
                if isinstance(parsed, list):
                    chips.extend(str(c) for c in parsed)
            except Exception:
                pass
        else:
            text_lines.append(line)
    return "\n".join(text_lines).strip(), chips


class ChatResponse(BaseModel):
    reply: str
    chips: list[str] = []
    intent: str
    agent: str        # friendly display name for the UI
    sources: list[str] = []
    agent_events: list[dict] = []


def _persist_messages(user_id: str, user_content: str, assistant_content: str, intent: str) -> None:
    """Encrypt and save the user message and assistant reply. Non-blocking."""
    try:
        from careerpilot.db.supabase import get_client
        from careerpilot.db.encryption import encrypt
        sb = get_client()
        sb.table("messages").insert([
            {"user_id": user_id, "role": "user", "content": encrypt(user_content), "intent": intent},
            {"user_id": user_id, "role": "assistant", "content": encrypt(assistant_content), "intent": intent},
        ]).execute()
    except Exception:
        pass


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    graph = get_graph()
    user_id = user.get("sub", request.user_id or "")
    lc_messages = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in request.messages
    ]
    initial_state = _build_initial_state(lc_messages, user_id)
    try:
        result = await graph.ainvoke(initial_state)
        raw_reply = result.get("response", "")
        reply, chips = _extract_chips(raw_reply)
        intent = result.get("intent", "chat")

        # Persist the last user turn + reply (clean text, no CHIPS lines)
        last_user_msg = next(
            (m.content for m in reversed(lc_messages) if isinstance(m, HumanMessage)), ""
        )
        if last_user_msg and reply:
            _persist_messages(user_id, last_user_msg, reply, intent)
            # Embed user message into ChromaDB for skill signal scanning
            import asyncio
            from careerpilot.db.message_store import store_message
            asyncio.get_event_loop().create_task(store_message(user_id, last_user_msg, intent))

        agent_display = result.get("agent_display") or AGENT_DISPLAY_NAMES.get(result.get("agent", ""), "Coach")
        return ChatResponse(
            reply=reply,
            chips=chips,
            intent=intent,
            agent=agent_display,
            sources=result.get("sources", []),
            agent_events=result.get("agent_events", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _fetch_user_phase(user_id: str) -> tuple[str, bool]:
    """Return (phase, intake_complete) from the users table, defaulting to intake.
    Auto-advances goal_setup → active if the user already has a saved plan."""
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        rows = sb.table("users").select("phase, intake_complete").eq("id", user_id).limit(1).execute()
        if rows.data:
            d = rows.data[0]
            phase = d.get("phase", "intake")
            intake_complete = bool(d.get("intake_complete", False))
            # If stuck in goal_setup but a plan already exists, advance to active
            if phase in ("goal_setup", "goal_planner"):
                has_plan = sb.table("goal_plan").select("id").eq("user_id", user_id).limit(1).execute()
                if has_plan.data:
                    sb.table("users").update({"phase": "active"}).eq("id", user_id).execute()
                    phase = "active"
            return phase, intake_complete
    except Exception:
        pass
    return "intake", False


def _build_initial_state(lc_messages: list, user_id: str) -> dict:
    phase, intake_complete = _fetch_user_phase(user_id)
    return {
        "messages": lc_messages,
        "user_id": user_id,
        "intent": "",
        "agent": "",
        "days_since": None,
        "days_left": None,
        "mood_score": None,
        "energy_score": None,
        "open_tasks": None,
        "resume_text": None,
        "linkedin_text": None,
        "tracking_summary": None,
        "intake_complete": intake_complete,
        "phase": phase,
        "response": "",
        "sources": [],
        "agent_events": [],
    }


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: dict = Depends(get_current_user)):
    """SSE endpoint — streams agent routing decisions in real time, then the final reply."""
    graph = get_graph()
    user_id = user.get("sub", request.user_id or "")
    lc_messages = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in request.messages
    ]
    initial_state = _build_initial_state(lc_messages, user_id)

    async def event_gen():
        routing: dict = {}
        try:
            async for ev in graph.astream_events(initial_state, version="v2"):
                etype = ev.get("event", "")
                name = ev.get("name", "")

                # Orchestrator finished deciding → emit agent routing event immediately
                if etype == "on_chain_end" and name == "orchestrator":
                    output = ev.get("data", {}).get("output", {})
                    routing.update(output)
                    evts = output.get("agent_events", [])
                    if evts:
                        yield f"data: {_json.dumps({'type': 'agent_event', **evts[-1]})}\n\n"

                # Agent node finished → emit final reply
                elif etype == "on_chain_end" and name in AGENT_MAP:
                    output = ev.get("data", {}).get("output", {})
                    raw_reply = output.get("response", "")
                    reply, chips = _extract_chips(raw_reply)
                    intent = routing.get("intent", "chat")
                    agent_display = (
                        routing.get("agent_display")
                        or AGENT_DISPLAY_NAMES.get(routing.get("agent", ""), "Coach")
                    )
                    sources = output.get("sources", [])
                    phase = output.get("phase", "")
                    needs_plan_refresh = bool(output.get("needs_plan_refresh", False))

                    last_user_msg = next(
                        (m.content for m in reversed(lc_messages) if isinstance(m, HumanMessage)), ""
                    )
                    if last_user_msg and reply:
                        _persist_messages(user_id, last_user_msg, reply, intent)
                        import asyncio
                        from careerpilot.db.message_store import store_message
                        asyncio.get_event_loop().create_task(
                            store_message(user_id, last_user_msg, intent)
                        )

                    yield f"data: {_json.dumps({'type': 'done', 'reply': reply, 'chips': chips, 'intent': intent, 'agent': agent_display, 'sources': sources, 'phase': phase, 'refresh_plan': needs_plan_refresh})}\n\n"

        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/history")
async def chat_history(
    limit: int = Query(default=10, le=50),
    user: dict = Depends(get_current_user),
):
    """Return the last N messages (pairs) for the authenticated user, oldest-first."""
    user_id = user.get("sub", "")
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        # Fetch limit*2 rows (each exchange = 2 rows), then reverse for chronological order
        from careerpilot.db.encryption import decrypt
        rows = (
            sb.table("messages")
            .select("role, content, intent, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit * 2)
            .execute()
        ).data or []
        for row in rows:
            row["content"] = decrypt(row["content"])
        return list(reversed(rows))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
