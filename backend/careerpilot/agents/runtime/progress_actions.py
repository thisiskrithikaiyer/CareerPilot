"""
Progress Actions — the write-path behind chat check-ins.

Extracts structured progress from a free-form check-in message, persists it to
daily_log + checkins, and closes matching plan tasks ("close the leetcode task").

extract_progress / match_task are kept side-effect free so the hard evals in
careerpilot/eval can assert exact behavior without a database.
"""
import json
import re
from datetime import date as _date

from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL

# Numeric fields shared with the daily_log table
COUNT_FIELDS = [
    "applications_sent",
    "networking_sent",
    "dsa_problems",
    "system_design_done",
    "interviews_attended",
    "mocks_done",
    "coffee_chat",
]

_EXTRACT_SYSTEM = """You extract structured job-search progress from a user's check-in message.

Output ONLY valid JSON with this exact schema — no markdown, no explanation:
{
  "applications_sent": <int>,
  "networking_sent": <int>,
  "dsa_problems": <int>,
  "system_design_done": <int>,
  "interviews_attended": <int>,
  "mocks_done": <int>,
  "coffee_chat": <int>,
  "mood_score": <int 1-10, or null>,
  "energy_score": <int 1-10, or null>,
  "wins": ["<thing that went well>"],
  "blockers": ["<thing blocking progress>"],
  "close_tasks": ["<task the user asked to mark done/closed>"],
  "notes": "<anything else worth remembering, or empty string>"
}

Rules:
- Counts: only what the user explicitly states. Never guess — default every int to 0.
- "applications" / "apps" / "applied to N jobs" → applications_sent.
- "leetcode" / "DSA" / "coding problems" solved → dsa_problems.
- "close the X task", "mark X done", "finished X", "done with X", "completed X"
  → append X (short phrase) to close_tasks.
- mood_score / energy_score ONLY when the user gives an explicit NUMBER
  ("mood is 7", "energy 4/10"). NEVER convert feelings into numbers:
  "exhausted", "tired", "drained", "feeling great" → mood_score: null, energy_score: null.
- wins/blockers: short phrases lifted from the message, not invented.
"""


def _parse_json_block(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()
    # Tolerate stray text around the object
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start:end + 1]
    return json.loads(raw)


def _empty_progress() -> dict:
    p = {f: 0 for f in COUNT_FIELDS}
    p.update({
        "mood_score": None,
        "energy_score": None,
        "wins": [],
        "blockers": [],
        "close_tasks": [],
        "notes": "",
    })
    return p


def _normalize(data: dict) -> dict:
    p = _empty_progress()
    for f in COUNT_FIELDS:
        try:
            p[f] = max(0, int(data.get(f) or 0))
        except (TypeError, ValueError):
            p[f] = 0
    for f in ("mood_score", "energy_score"):
        v = data.get(f)
        if isinstance(v, (int, float)) and 1 <= v <= 10:
            p[f] = int(v)
    for f in ("wins", "blockers", "close_tasks"):
        v = data.get(f)
        if isinstance(v, list):
            p[f] = [str(x).strip() for x in v if str(x).strip()][:8]
    p["notes"] = str(data.get("notes") or "").strip()[:500]
    return p


def extract_progress(text: str) -> dict:
    """LLM extraction of structured progress. Always returns the full schema."""
    if not text or not text.strip():
        return _empty_progress()
    try:
        resp = groq_complete(
            model=GROQ_MODEL,
            max_tokens=400,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": text},
            ],
        )
        return _normalize(_parse_json_block(resp.choices[0].message.content))
    except Exception:
        # Retry once without JSON mode (some models reject response_format)
        try:
            resp = groq_complete(
                model=GROQ_MODEL,
                max_tokens=400,
                temperature=0,
                messages=[
                    {"role": "system", "content": _EXTRACT_SYSTEM},
                    {"role": "user", "content": text},
                ],
            )
            return _normalize(_parse_json_block(resp.choices[0].message.content))
        except Exception as e:
            print(f"[PROGRESS] extraction failed: {e}")
            return _empty_progress()


def has_progress(p: dict) -> bool:
    return (
        any(p.get(f, 0) for f in COUNT_FIELDS)
        or p.get("mood_score") is not None
        or p.get("energy_score") is not None
        or bool(p.get("wins"))
        or bool(p.get("blockers"))
        or bool(p.get("notes"))
    )


# ── Deterministic task matching (no LLM — hard-evaluable) ─────────────────────

_STOP_WORDS = {
    "the", "a", "an", "my", "task", "tasks", "close", "mark", "done", "finish",
    "finished", "complete", "completed", "with", "off", "as", "for", "today",
    "todays", "please", "can", "you", "i", "im", "is", "of", "and", "to",
}

# Canonical vocab so "dsa"/"lc" hit "Leetcode: Arrays" and "apps" hits "Job applications"
_CANON = {
    "lc": "leetcode", "dsa": "leetcode", "coding": "leetcode", "algorithms": "leetcode",
    "algo": "leetcode", "problems": "leetcode",
    "app": "applications", "apps": "applications", "application": "applications",
    "applications": "applications", "apply": "applications", "applying": "applications",
    "job": "applications", "jobs": "applications",
    "outreach": "networking", "messages": "networking", "network": "networking",
    "networking": "networking", "referral": "referral", "referrals": "referral",
    "behavioural": "behavioral", "star": "behavioral",
    "sysdesign": "design", "sd": "design",
    "mock": "mock", "mocks": "mock",
    "wellness": "wellness", "walk": "wellness", "journal": "wellness",
    "tracker": "log", "logging": "log",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {_CANON.get(w, w) for w in words if w not in _STOP_WORDS}


def match_task(request: str, schedule: dict, task_status: dict | None = None):
    """Find the open schedule task best matching a close request.

    Returns (task_key, label) e.g. ("morning-0", "Leetcode: Arrays (60min)"),
    or None when nothing overlaps. Deterministic: word-overlap scoring with
    canonical synonyms, ties broken by schedule order.
    """
    task_status = task_status or {}
    req = _tokens(request)
    if not req:
        return None
    best, best_score = None, 0
    for block in ("morning", "midday", "evening"):
        tasks = (schedule or {}).get(block, {}).get("tasks", []) or []
        for i, label in enumerate(tasks):
            key = f"{block}-{i}"
            if task_status.get(key):
                continue  # already closed
            score = len(req & _tokens(label))
            if score > best_score:
                best, best_score = (key, label), score
    return best


# ── DB writes ─────────────────────────────────────────────────────────────────

def apply_progress(user_id: str, progress: dict, for_date: str | None = None) -> dict:
    """Persist extracted progress: increment daily_log counts, insert a checkin row.

    Returns a summary dict of what was actually written (used in the coach reply).
    """
    from datetime import datetime, timezone
    from careerpilot.db.supabase import get_client

    sb = get_client()
    log_date = for_date or _date.today().isoformat()
    saved: dict = {"date": log_date, "log_updates": {}, "checkin_saved": False}

    # 1. daily_log — additive upsert so repeated check-ins accumulate
    if any(progress.get(f, 0) for f in COUNT_FIELDS) or progress.get("notes"):
        existing = (
            sb.table("daily_log")
            .select("*")
            .eq("user_id", user_id)
            .eq("date", log_date)
            .limit(1)
            .execute()
        ).data
        row = existing[0] if existing else {}
        update = {"user_id": user_id, "date": log_date}
        for f in COUNT_FIELDS:
            inc = progress.get(f, 0)
            if inc:
                update[f] = (row.get(f) or 0) + inc
                saved["log_updates"][f] = update[f]
        if progress.get("notes"):
            prior = (row.get("notes") or "").strip()
            update["notes"] = f"{prior}\n{progress['notes']}".strip()
        # Keep legacy mirror columns in sync (signal_analyzer reads these)
        if "applications_sent" in update:
            update["apps_done"] = update["applications_sent"]
        if "networking_sent" in update:
            update["networking_done"] = update["networking_sent"]
        if "dsa_problems" in update:
            update["leetcode_done"] = update["dsa_problems"]
        if "interviews_attended" in update:
            update["interviews_attended"] = update["interviews_attended"]
        sb.table("daily_log").upsert(update, on_conflict="user_id,date").execute()

    # 2. checkins — mood/energy/wins/blockers
    if (
        progress.get("mood_score") is not None
        or progress.get("energy_score") is not None
        or progress.get("wins")
        or progress.get("blockers")
    ):
        sb.table("checkins").insert({
            "user_id": user_id,
            "mood_score": progress.get("mood_score") or 5,
            "energy_score": progress.get("energy_score") or 5,
            "wins": progress.get("wins") or [],
            "blockers": progress.get("blockers") or [],
            "notes": progress.get("notes") or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        saved["checkin_saved"] = True

    return saved


def close_plan_tasks(user_id: str, close_requests: list[str], for_date: str | None = None) -> list[str]:
    """Close plan tasks matching the user's requests. Returns the labels closed."""
    from careerpilot.db.supabase import get_client

    if not close_requests:
        return []
    sb = get_client()
    plan_date = for_date or _date.today().isoformat()
    rows = (
        sb.table("plans")
        .select("id, plan_json, schedule")
        .eq("user_id", user_id)
        .eq("date", plan_date)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    if not rows:
        return []
    plan = rows[0]
    plan_json = plan.get("plan_json") or {}
    schedule = plan.get("schedule") or {}
    task_status = dict(plan_json.get("task_status") or {})

    closed: list[str] = []
    for req in close_requests:
        hit = match_task(req, schedule, task_status)
        if hit:
            key, label = hit
            task_status[key] = True
            closed.append(label)

    if closed:
        plan_json["task_status"] = task_status
        sb.table("plans").update({"plan_json": plan_json}).eq("id", plan["id"]).execute()
    return closed


def open_task_labels(user_id: str, for_date: str | None = None, limit: int = 5) -> list[str]:
    """Remaining (unclosed) tasks on today's plan — used for proactive nudges."""
    from careerpilot.db.supabase import get_client

    sb = get_client()
    plan_date = for_date or _date.today().isoformat()
    rows = (
        sb.table("plans")
        .select("plan_json, schedule")
        .eq("user_id", user_id)
        .eq("date", plan_date)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    if not rows:
        return []
    schedule = rows[0].get("schedule") or {}
    task_status = (rows[0].get("plan_json") or {}).get("task_status") or {}
    remaining = []
    for block in ("morning", "midday", "evening"):
        for i, label in enumerate(schedule.get(block, {}).get("tasks", []) or []):
            if not task_status.get(f"{block}-{i}"):
                remaining.append(label)
    return remaining[:limit]
