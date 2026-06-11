"""
Carryover — pure logic comparing the previous day's plan against what was
actually completed (task_status checkboxes + daily_log counts), so the next
plan builds on real progress instead of assuming everything planned got done.

No DB and no LLM in this module — the hard evals in careerpilot/eval assert
exact behavior on these functions.
"""

# Routine/meta tasks never carry over to the next day
_ROUTINE_MARKERS = (
    "log today",
    "review applications sent",
    "wellness",
    "walk",
    "journal",
)


def _is_routine(label: str) -> bool:
    low = label.lower()
    return any(m in low for m in _ROUTINE_MARKERS)


def compute_carryover(prev_plan_json: dict | None, prev_schedule: dict | None, prev_log: dict | None) -> dict:
    """Diff yesterday's plan against evidence of completion.

    Evidence sources, in priority order:
      1. task_status — explicit checkbox/chat closes ("morning-0": true)
      2. daily_log counts — e.g. dsa_problems >= planned count means the
         leetcode topic was actually worked, even if no checkbox was ticked.
    """
    plan = prev_plan_json or {}
    schedule = prev_schedule or {}
    log = prev_log or {}
    task_status = plan.get("task_status") or {}

    completed: list[str] = []
    missed: list[str] = []
    for block in ("morning", "midday", "evening"):
        tasks = schedule.get(block, {}).get("tasks", []) or []
        for i, label in enumerate(tasks):
            if task_status.get(f"{block}-{i}"):
                completed.append(label)
            else:
                missed.append(label)

    apps_done = log.get("applications_sent") or log.get("apps_done") or 0
    dsa_done = log.get("dsa_problems") or log.get("leetcode_done") or 0
    sd_done = log.get("system_design_done") or 0
    sd_topic_logged = bool((log.get("system_design_topic") or "").strip())

    apps_target = plan.get("job_apps") or 0
    lc_target = plan.get("leetcode_problems") or 0
    lc_topic = plan.get("leetcode_topic")
    sd_concept = plan.get("system_design_concept")

    lc_task_closed = any("leetcode" in t.lower() for t in completed)
    sd_task_closed = any("design" in t.lower() for t in completed)
    apps_task_closed = any("application" in t.lower() for t in completed)

    lc_topic_completed = bool(lc_topic) and (
        lc_task_closed or (lc_target > 0 and dsa_done >= lc_target) or (lc_target == 0 and dsa_done > 0)
    )
    sd_concept_completed = bool(sd_concept) and (sd_task_closed or sd_done > 0 or sd_topic_logged)

    apps_shortfall = 0 if apps_task_closed else max(0, apps_target - apps_done)

    carryover_tasks = [t for t in missed if not _is_routine(t)]
    # Don't carry tasks whose underlying work the log proves was done
    if lc_topic_completed:
        carryover_tasks = [t for t in carryover_tasks if "leetcode" not in t.lower()]
    if sd_concept_completed:
        carryover_tasks = [t for t in carryover_tasks if "design" not in t.lower()]
    if apps_shortfall == 0:
        carryover_tasks = [t for t in carryover_tasks if "application" not in t.lower()]
    carryover_tasks = carryover_tasks[:4]

    total_tasks = len(completed) + len(missed)
    completion_rate = round(len(completed) / total_tasks, 2) if total_tasks else None

    return {
        "completed_yesterday": completed,
        "missed_yesterday": missed,
        "carryover_tasks": carryover_tasks,
        "completion_rate": completion_rate,
        "apps_done": apps_done,
        "apps_target": apps_target,
        "apps_shortfall": apps_shortfall,
        "dsa_done": dsa_done,
        "lc_topic": lc_topic,
        "lc_topic_completed": lc_topic_completed,
        "sd_concept": sd_concept,
        "sd_concept_completed": sd_concept_completed,
    }


def adjust_targets_for_carryover(targets: dict, carryover: dict) -> dict:
    """Fold yesterday's shortfall into today's targets (capped so one bad day
    doesn't snowball into an impossible plan)."""
    adjusted = dict(targets)
    shortfall = carryover.get("apps_shortfall") or 0
    if shortfall > 0:
        adjusted["job_apps"] = (targets.get("job_apps") or 8) + min(shortfall, 4)
    return adjusted
