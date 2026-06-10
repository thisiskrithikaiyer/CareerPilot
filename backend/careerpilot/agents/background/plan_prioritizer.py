"""
Plan Prioritizer — takes signals and decides what the day should focus on.
Returns a priority_mode and adjusted targets. No LLM needed — pure logic.
"""


MODES = {
    "interview_prep":    "Interview tomorrow — everything else is secondary",
    "fix_resume":        "Resume/LinkedIn weak — fix before more apps",
    "shift_to_prep":     "Too many apps, no callbacks — stop applying, fix fundamentals",
    "fix_failing":       "Passing screens but failing technical — deep prep on weak topics",
    "burnout_recovery":  "Burned out — reduced load, wellness first",
    "standard":          "On track — execute the plan",
}


def prioritize(signals: dict) -> dict:
    s = signals

    # ── Priority 1: Interview tomorrow ───────────────────────────────────────
    if s.get("interviews_tomorrow", 0) > 0:
        topics = s.get("interview_topics_tomorrow") or ["system design", "algorithms"]
        return {
            "priority_mode": "interview_prep",
            "mode_reason": f"Interview scheduled tomorrow. Topics: {', '.join(topics)}",
            "adjusted_targets": {
                "job_apps": max(2, s["app_target"] // 4),        # minimal apps
                "networking": max(1, s["net_target"] // 3),
                "leetcode_problems": s["lc_target"] + 1,          # extra problem
                "system_design": 2,                                 # double system design
                "behavioral_questions": 3,
                "interview_focus_topics": topics,
            },
        }

    # ── Priority 2: Burned out ────────────────────────────────────────────────
    if s.get("burned_out"):
        return {
            "priority_mode": "burnout_recovery",
            "mode_reason": f"Avg mood {s['avg_mood']}/10, energy {s['avg_energy']}/10 — {s['low_energy_days']} low-energy days",
            "adjusted_targets": {
                "job_apps": max(2, s["app_target"] // 3),
                "networking": 2,
                "leetcode_problems": 1,
                "system_design": 0,
                "behavioral_questions": 1,
                "wellness_block": True,
            },
        }

    # ── Priority 3: Too many apps, zero interviews ────────────────────────────
    if s.get("too_many_apps_no_callbacks"):
        fix = []
        if s.get("resume_weak"):
            fix.append("resume rewrite")
        if s.get("linkedin_weak"):
            fix.append("LinkedIn headline + About")
        fix = fix or ["resume and LinkedIn audit"]
        return {
            "priority_mode": "fix_resume" if (s.get("resume_weak") or s.get("linkedin_weak")) else "shift_to_prep",
            "mode_reason": f"{s['total_apps_7d']} apps in 7 days, 0 interviews. Fix: {', '.join(fix)}",
            "adjusted_targets": {
                "job_apps": 3,                                    # minimal — focus is fixing
                "networking": s["net_target"],
                "leetcode_problems": s["lc_target"],
                "system_design": 1,
                "behavioral_questions": 2,
                "fix_tasks": fix,
            },
        }

    # ── Priority 4: Failing interviews ───────────────────────────────────────
    if s.get("interview_failing"):
        weak = s.get("failed_topics") or ["unknown — review all recent screens"]
        return {
            "priority_mode": "fix_failing",
            "mode_reason": f"Pass rate {s['pass_rate']}%. Failing on: {', '.join(weak)}",
            "adjusted_targets": {
                "job_apps": max(3, s["app_target"] // 2),
                "networking": max(2, s["net_target"] // 2),
                "leetcode_problems": s["lc_target"] + 1,
                "system_design": 2,
                "behavioral_questions": 2,
                "weak_topics_to_drill": weak,
            },
        }

    # ── Priority 5: No interview in 14 days ──────────────────────────────────
    if s.get("no_interview_14d"):
        return {
            "priority_mode": "fix_resume",
            "mode_reason": f"{s.get('days_since_interview', '14+')} days with no interview — resume or targeting issue",
            "adjusted_targets": {
                "job_apps": s["app_target"],
                "networking": s["net_target"] + 2,               # push networking harder
                "leetcode_problems": s["lc_target"],
                "system_design": 1,
                "behavioral_questions": 1,
                "fix_tasks": ["resume targeting audit", "referral outreach"],
            },
        }

    # ── Default: standard execution ───────────────────────────────────────────
    return {
        "priority_mode": "standard",
        "mode_reason": "On track — execute the plan",
        "adjusted_targets": {
            "job_apps": s["app_target"],
            "networking": s["net_target"],
            "leetcode_problems": s["lc_target"],
            "system_design": 1,
            "behavioral_questions": 1,
        },
    }
