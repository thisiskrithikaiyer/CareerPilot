"""
Schedule Builder — takes priority mode + targets and builds morning/midday/evening blocks.
Uses LLM only for the coach note. Block structure is deterministic.
"""
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL


def _block(time: str, tasks: list[str]) -> dict:
    return {"time": time, "tasks": tasks}


def _task(label: str, duration_min: int, detail: str = "") -> str:
    base = f"{label} ({duration_min}min)"
    return f"{base} — {detail}" if detail else base


def build_schedule(priority: dict, signals: dict, next_lc: dict, behavioral: str) -> dict:
    mode = priority["priority_mode"]
    targets = priority["adjusted_targets"]

    lc_problems = targets.get("leetcode_problems", 2)
    lc_topic = next_lc["topic"]
    lc_suggested = next_lc["problems"][:lc_problems]
    apps = targets.get("job_apps", 8)
    networking = targets.get("networking", 5)
    sd = targets.get("system_design", 1)
    behavioral_q = targets.get("behavioral_questions", 1)
    wellness = targets.get("wellness_block", False)
    weak_topics = targets.get("weak_topics_to_drill") or targets.get("interview_focus_topics") or []
    fix_tasks = targets.get("fix_tasks", [])

    # ── MORNING (deep work — hardest cognitive tasks) ─────────────────────────
    morning_tasks = []

    if mode == "interview_prep":
        morning_tasks += [
            _task(f"Leetcode: {lc_topic}", 60, f"Solve: {', '.join(lc_suggested)}"),
            _task("System design deep dive", 60, f"Topic: {', '.join(weak_topics) or 'general'}"),
        ]
    elif mode == "burnout_recovery":
        morning_tasks += [
            _task("Light walk or exercise", 30),
            _task(f"Leetcode: {lc_topic}", 40, f"1 problem only: {lc_suggested[0] if lc_suggested else ''}"),
        ]
    elif mode in ("fix_resume", "shift_to_prep"):
        fix_detail = ", ".join(fix_tasks) if fix_tasks else "resume audit"
        morning_tasks += [
            _task("Resume/LinkedIn fix", 90, fix_detail),
        ]
    elif mode == "fix_failing":
        drill = ", ".join(weak_topics) if weak_topics else "review failed screens"
        morning_tasks += [
            _task(f"Drill weak topics: {drill}", 60),
            _task(f"Leetcode: {lc_topic}", 50, f"Solve: {', '.join(lc_suggested)}"),
        ]
    else:
        morning_tasks += [
            _task(f"Leetcode: {lc_topic}", 60, f"Solve: {', '.join(lc_suggested)}"),
        ]
        if sd:
            morning_tasks.append(_task("System design", 45))

    # ── MIDDAY (applications + networking) ───────────────────────────────────
    midday_tasks = [
        _task(f"Job applications", 90, f"Send {apps} targeted applications"),
        _task(f"Networking outreach", 30, f"Send {networking} personalized messages"),
    ]

    if mode == "interview_prep":
        midday_tasks = [
            _task("Behavioral prep", 45, f"Practice: {behavioral}"),
            _task(f"Job applications", 45, f"Send {apps} targeted applications"),
        ]

    if fix_tasks and mode in ("fix_resume", "no_interview_14d"):
        midday_tasks.insert(0, _task("Referral outreach", 30, "Contact 3 warm connections for referrals"))

    # ── EVENING (review + prep for tomorrow) ─────────────────────────────────
    evening_tasks = [
        _task("Behavioral question practice", 30, f"Topic: {behavioral}"),
        _task("Review applications sent today", 15, "Note any follow-ups needed"),
        _task("Log today's activity", 10, "Update daily tracker"),
    ]

    if sd and mode not in ("interview_prep", "burnout_recovery"):
        evening_tasks.insert(0, _task("System design review", 45, "1 design problem end-to-end"))

    if wellness:
        evening_tasks.append(_task("Wellness — no screens", 30, "Walk, journal, or call someone"))

    if mode == "interview_prep":
        evening_tasks = [
            _task("Mock interview simulation", 60, f"Full interview: {', '.join(weak_topics) or 'general'}"),
            _task("Behavioral: STAR stories", 30, f"Topic: {behavioral}"),
            _task("Log today's activity", 10),
        ]

    schedule = {
        "morning": _block("Morning (9am–12pm)", morning_tasks),
        "midday": _block("Midday (12pm–4pm)", midday_tasks),
        "evening": _block("Evening (7pm–9pm)", evening_tasks),
    }

    return schedule


def build_coach_note(signals: dict, priority: dict) -> str:
    try:
        context = (
            f"Priority mode: {priority['priority_mode']}\n"
            f"Reason: {priority['mode_reason']}\n"
            f"Burnout rate: {signals.get('burnout_rate')}/10\n"
            f"Pass rate: {signals.get('pass_rate')}%\n"
            f"Days since last interview: {signals.get('days_since_interview')}\n"
            f"Apps last 7 days: {signals.get('total_apps_7d')}"
        )
        resp = groq_complete(
            model=GROQ_MODEL,
            max_tokens=80,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a direct job-search coach. Write one sharp coaching note (2 sentences max). "
                        "Name the biggest issue and what to do about it today. No fluff."
                    ),
                },
                {"role": "user", "content": context},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return priority["mode_reason"]
