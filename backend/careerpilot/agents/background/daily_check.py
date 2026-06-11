"""
Daily Plan Builder — orchestrates sub-agents to build tomorrow's smart daily plan.

Flow:
  1. signal_analyzer  → reads all DB data, computes signals
  2. carryover        → diffs the previous plan against what was ACTUALLY completed
  3. plan_prioritizer → determines priority mode + adjusted targets (pure logic)
  4. planner          → determines next leetcode topic from curriculum
  5. schedule_builder → builds morning/midday/evening time blocks (+ carryover)
  6. saves to plans table with full schedule, signals, priority_mode
"""
from datetime import date, timedelta

from careerpilot.agents.background.signal_analyzer import analyze
from careerpilot.agents.background.plan_prioritizer import prioritize
from careerpilot.agents.background.schedule_builder import build_schedule, build_coach_note
from careerpilot.agents.background.planner import BEHAVIORAL_ROTATION, _get_behavioral_focus
from careerpilot.agents.background.role_curriculum import get_next_topic, get_next_system_design, detect_role_type
from careerpilot.agents.background.carryover import compute_carryover, adjust_targets_for_carryover


def _load_previous_day(sb, user_id: str, plan_date: str) -> tuple[dict | None, dict | None, dict | None]:
    """Most recent plan before plan_date, plus that day's activity log."""
    prev_rows = (
        sb.table("plans")
        .select("date, plan_json, schedule")
        .eq("user_id", user_id)
        .lt("date", plan_date)
        .order("date", desc=True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    if not prev_rows:
        return None, None, None
    prev = prev_rows[0]
    log_rows = (
        sb.table("daily_log")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", prev["date"])
        .limit(1)
        .execute()
    ).data or []
    return prev.get("plan_json"), prev.get("schedule"), (log_rows[0] if log_rows else None)


async def build_daily_plan(user_id: str, for_date: str | None = None) -> dict:
    from careerpilot.db.supabase import get_client
    sb = get_client()

    today = date.fromisoformat(for_date) if for_date else date.today()
    plan_date = today.isoformat()

    # ── 1. Analyze signals ────────────────────────────────────────────────────
    signals = await analyze(user_id, sb)

    # ── 1b. Carryover — what did the previous plan's day actually complete? ──
    prev_plan_json, prev_schedule, prev_log = _load_previous_day(sb, user_id, plan_date)
    carryover = compute_carryover(prev_plan_json, prev_schedule, prev_log)

    # ── 2. Determine priority ─────────────────────────────────────────────────
    priority = prioritize(signals)
    priority["adjusted_targets"] = adjust_targets_for_carryover(
        priority.get("adjusted_targets") or {}, carryover
    )

    # ── 3. Curriculum progression ─────────────────────────────────────────────
    profile = (
        sb.table("users")
        .select("search_start_date")
        .eq("id", user_id)
        .single()
        .execute()
    ).data or {}
    days_since_start = 0
    if profile.get("search_start_date"):
        days_since_start = (today - date.fromisoformat(profile["search_start_date"])).days

    # Read role + curriculum from goal plan (embedded at plan creation time)
    goal_for_role = (
        sb.table("goal_plan")
        .select("goal_stratergy")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    goal_stratergy = (goal_for_role[0].get("goal_stratergy") or {}) if goal_for_role else {}
    role_targets = goal_stratergy.get("role_targets", {})
    role_text = role_targets.get("realistic") or role_targets.get("stretch") or ""

    # Use embedded curriculum if available, fall back to re-detecting from role text
    embedded = goal_stratergy.get("curriculum")
    if embedded:
        from careerpilot.agents.background.role_curriculum import detect_role_type
        _lc_topics = embedded["leetcode_topics"]
        _sd_concepts = embedded["system_design_concepts"]
        _role_type = goal_stratergy.get("role_type") or detect_role_type(role_text)

        def get_next_topic(_, completed):  # type: ignore[override]
            done = {t.lower() for t in completed}
            for t in _lc_topics:
                if t["topic"].lower() not in done:
                    return t
            return _lc_topics[-1]

        def get_next_system_design(_, completed):  # type: ignore[override]
            done = {c.lower() for c in completed}
            for c in _sd_concepts:
                if c["concept"].lower() not in done:
                    return c
            return _sd_concepts[-1]
    else:
        _role_type = detect_role_type(role_text)

    past_plans = (
        sb.table("plans")
        .select("plan_json")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(30)
        .execute()
    ).data or []
    completed_lc_topics = list({
        p["plan_json"]["leetcode_topic"]
        for p in past_plans
        if p.get("plan_json") and p["plan_json"].get("leetcode_topic")
    })
    completed_sd_concepts = list({
        p["plan_json"]["system_design_concept"]
        for p in past_plans
        if p.get("plan_json") and p["plan_json"].get("system_design_concept")
    })

    # Planned ≠ done: if yesterday's topic/concept wasn't actually completed
    # (no closed task, no logged work), keep serving it instead of advancing.
    if carryover.get("lc_topic") and not carryover.get("lc_topic_completed"):
        completed_lc_topics = [t for t in completed_lc_topics if t != carryover["lc_topic"]]
    if carryover.get("sd_concept") and not carryover.get("sd_concept_completed"):
        completed_sd_concepts = [c for c in completed_sd_concepts if c != carryover["sd_concept"]]

    next_lc = get_next_topic(role_text, completed_lc_topics)
    next_sd = get_next_system_design(role_text, completed_sd_concepts)
    behavioral = _get_behavioral_focus(days_since_start)

    # ── 4. Build time-blocked schedule ───────────────────────────────────────
    schedule = build_schedule(priority, signals, next_lc, behavioral)

    # Unfinished work rolls forward — carryover tasks lead the morning block so
    # the day starts by closing yesterday's gaps.
    if carryover.get("carryover_tasks"):
        morning = schedule.get("morning", {"time": "Morning (9am–12pm)", "tasks": []})
        morning["tasks"] = [
            f"Carryover from yesterday: {t}" for t in carryover["carryover_tasks"]
        ] + morning.get("tasks", [])
        schedule["morning"] = morning

    coach_note = build_coach_note(signals, priority, carryover)

    # ── 5. Compose plan_json ──────────────────────────────────────────────────
    targets = priority["adjusted_targets"]
    lc_count = targets.get("leetcode_problems", 2)
    plan_json = {
        "date": plan_date,
        "priority_mode": priority["priority_mode"],
        "mode_reason": priority["mode_reason"],
        "role_type": _role_type,
        "job_apps": targets.get("job_apps", 8),
        "networking": targets.get("networking", 5),
        "leetcode_problems": lc_count,
        "leetcode_topic": next_lc["topic"],
        "leetcode_suggested": next_lc["problems"][:lc_count],
        "leetcode_skills": next_lc.get("skills", []),
        "system_design": targets.get("system_design", 1),
        "system_design_concept": next_sd["concept"],
        "system_design_key_points": next_sd["key_points"],
        "system_design_skills": next_sd.get("skills", []),
        "behavioral_focus": behavioral,
        "coach_note": coach_note,
        # Completion-aware planning state
        "task_status": {},
        "carryover_tasks": carryover.get("carryover_tasks", []),
        "completed_yesterday": carryover.get("completed_yesterday", []),
        "yesterday_completion_rate": carryover.get("completion_rate"),
    }

    # ── 6. Save to plans table ────────────────────────────────────────────────
    plan_row = sb.table("plans").insert({
        "user_id": user_id,
        "date": plan_date,
        "coach_note": coach_note,
        "plan_json": plan_json,
        "schedule": schedule,
        "priority_mode": priority["priority_mode"],
        "signals": signals,
    }).execute()
    plan_id = plan_row.data[0]["id"]

    # ── 7. Update goal_plan.goal_stratergy with current daily plan ────────────
    latest_goal = (
        sb.table("goal_plan")
        .select("id, goal_stratergy")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    if latest_goal:
        existing = latest_goal[0].get("goal_stratergy") or {}
        existing["current_daily_plan"] = plan_json
        sb.table("goal_plan").update({"goal_stratergy": existing}).eq("id", latest_goal[0]["id"]).execute()

    print(f"[DAILY PLAN] user={user_id} | mode={priority['priority_mode']} | lc={next_lc['topic']}")
    return {"plan_id": plan_id, "plan": plan_json, "schedule": schedule}


# Keep backward compat — plan_worker calls generate_plan
async def aggregate_for_user(user_id: str) -> dict:
    return await build_daily_plan(user_id)
