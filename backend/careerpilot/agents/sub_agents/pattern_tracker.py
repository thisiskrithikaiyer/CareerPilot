"""Pattern tracker sub-agent — conversational pattern coach + low-level detect utility."""
import json
from langchain_core.messages import HumanMessage
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.prompts.loader import load_prompt


async def run(state: State) -> dict:
    user_id = state.get("user_id", "")
    base = load_prompt("pattern_tracker.txt")

    pattern_section = ""
    if user_id:
        try:
            data = await detect_patterns(user_id)
            pattern_section = f"\n\nBEHAVIORAL DATA (last 14 days):\n{json.dumps(data, indent=2)}"
        except Exception:
            pattern_section = "\n\n(Pattern data unavailable — DB unreachable or insufficient history)"

    system = base + pattern_section

    history = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state["messages"]
    ]
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=400,
        messages=[{"role": "system", "content": system}, *history],
    )
    return {"response": resp.choices[0].message.content, "sources": []}


async def detect_patterns(user_id: str) -> dict:
    """
    Analyze last 14 days of check-ins and plan completion rates.
    Returns detected patterns and one coaching nudge.
    """
    from careerpilot.db.supabase import get_client
    from datetime import date, timedelta
    import json

    sb = get_client()
    two_weeks_ago = (date.today() - timedelta(days=14)).isoformat()

    checkins = (
        sb.table("checkins")
        .select("mood_score, energy_score, blockers, created_at")
        .eq("user_id", user_id)
        .gte("created_at", two_weeks_ago)
        .order("created_at")
        .execute()
    )

    tasks = (
        sb.table("plan_tasks")
        .select("completed, category, created_at")
        .eq("user_id", user_id)
        .gte("created_at", two_weeks_ago)
        .execute()
    )

    total_tasks = len(tasks.data)
    completed_tasks = sum(1 for t in tasks.data if t["completed"])
    completion_rate = round(completed_tasks / total_tasks, 2) if total_tasks > 0 else 0

    context = json.dumps({
        "checkins": checkins.data,
        "task_completion_rate": completion_rate,
        "total_tasks": total_tasks,
    }, default=str)

    system = (
        "Analyze this job-seeker's behavioral data over 14 days. "
        "Identify 1-2 specific patterns (positive or concerning). "
        'Output JSON: {"patterns": [...], "coaching_nudge": "..."}. '
        "Be specific. No generic observations."
    )
    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=256,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": context},
        ],
    )
    import json as _json
    result = _json.loads(resp.choices[0].message.content)
    result["completion_rate"] = completion_rate
    return result
