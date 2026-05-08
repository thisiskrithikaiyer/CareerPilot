"""
Weekly target recalibrator — computes daily_targets from deadline + funnel math.

Core idea:
  Work backwards from 1 offer using PROFILE-DERIVED rates (not fixed industry averages):
    screen_rate  = f(experience_band, resume_score)   — senior+strong resume → higher
    pass_rate    = f(leetcode_level)                  — advanced → higher
    rounds       = f(target_role tier)                — FAANG=7, startup=3
    lc_goal      = f(role, band, leetcode_level)      — SWE fundamentals → 120, advanced MLE → 50

  Pipeline math:
    pipeline_success_p   = pass_rate ^ rounds
    pipelines_needed     = ceil(1 / pipeline_success_p)
    apps_needed          = ceil(pipelines_needed / screen_rate)
    apps_per_day         = ceil(apps_needed / days_left)

  Active pipeline deduction:
    active_pipelines = distinct companies with interviews in last 14 days
    remaining_apps   = ceil((pipelines_needed - active_pipelines) / screen_rate)
    prep_boost_lc    = min(2, active_pipelines // 2)

  Funnel leak diagnosis (from signal_analyzer LLM diagnosis):
    Burned out        → everything reduced
    Interview tomorrow → everything pivots to prep
    Low screen rate   → resume problem → push networking
    Low pass rate     → interview problem → push prep
    No interview 14d  → volume or resume → push apps + networking

Runs:
  1. Immediately after goal commitment (first calibration)
  2. Every Sunday at 6 AM via APScheduler

Writes to: goal_plan.goal_stratergy.daily_targets
           users.belief_state (Bayesian-updated rates + LLM diagnosis)
"""
import math
import logging
from datetime import date, timedelta

from crisiscoach.agents.background.signal_analyzer import analyze

logger = logging.getLogger(__name__)

# Hard caps (safety rails, not strategy)
_MAX_APPS_PER_DAY = 20
_MIN_APPS_PER_DAY = 2
_LC_HORIZON_DAYS = 60   # plan horizon cap — longer runway doesn't mean easier pace


# ── Level 1: Profile-derived estimation functions ─────────────────────────────

def _estimate_screen_rate(experience_band: str | None, resume_score: int | None) -> float:
    """
    Fraction of applications that lead to a phone screen.
    Senior engineers with strong resumes convert at 2x the rate of junior engineers with weak ones.
    """
    base = {
        "junior":     0.07,
        "mid":        0.10,
        "senior":     0.14,
        "staff_plus": 0.18,
    }.get(experience_band or "mid", 0.10)
    if resume_score is not None:
        if resume_score >= 8:
            base = min(0.25, base * 1.3)
        elif resume_score <= 4:
            base = max(0.03, base * 0.65)
    return round(base, 3)


def _estimate_pass_rate(leetcode_level: str | None) -> float:
    """
    Estimated per-round pass rate based on current technical ability.
    Someone who can't do Two Sum will fail most technical rounds; advanced candidates pass ~65%.
    """
    return {
        "fundamentals": 0.25,
        "building":     0.35,
        "standard":     0.50,
        "advanced":     0.65,
    }.get(leetcode_level or "standard", 0.50)


def _estimate_rounds(realistic_role: str | None) -> int:
    """
    Typical rounds per offer based on target role/company tier.
    FAANG runs 6-7 rounds; startups do 2-3; mid-size is 4-5.
    """
    role = (realistic_role or "").lower()
    if any(c in role for c in ["google", "meta", "apple", "amazon", "microsoft", "openai", "stripe", "faang"]):
        return 7
    if "staff" in role or "principal" in role:
        return 6
    if "senior" in role:
        return 5
    if any(w in role for w in ["startup", "early stage", "seed"]):
        return 3
    return 4  # mid-size default


def _estimate_lc_goal(role: str | None, experience_band: str | None, leetcode_level: str | None) -> int:
    """
    Total problems to solve before offer day.
    SWE needs more than MLE; fundamentals track needs more reps than advanced.
    """
    base = {
        "SWE":          80,
        "MLE":          65,
        "AI Engineer":  45,
        "Data Engineer": 70,
    }.get(role or "SWE", 75)
    factor = {
        "fundamentals": 1.5,    # needs more reps to build pattern recognition
        "building":     1.2,
        "standard":     1.0,
        "advanced":     0.75,   # quality > quantity for hards
    }.get(leetcode_level or "standard", 1.0)
    return round(base * factor)


# ── Derived target helpers ────────────────────────────────────────────────────

def _mode_from_deadline(days_left: int | None, days_since: int | None) -> str:
    dl = days_left if days_left is not None else 999
    ds = days_since or 0
    if dl <= 28 or ds >= 60:
        return "CRISIS"
    elif dl <= 56 or ds >= 30:
        return "URGENT"
    elif dl <= 120:
        return "STANDARD"
    else:
        return "STRATEGIC"


def _lc_per_day(days_left: int | None, leetcode_level: str | None, lc_goal: int = 75) -> int:
    """
    Daily leetcode target: whichever is higher — deadline-driven pace or level floor.
    Deadline-driven: ceil(lc_goal / horizon) — tighter deadline → more per day.
    Level floor: minimum 2/day regardless of how much runway exists.
    """
    horizon = min(days_left or _LC_HORIZON_DAYS, _LC_HORIZON_DAYS)
    deadline_driven = math.ceil(lc_goal / max(horizon, 1))
    return max(deadline_driven, 2)


def _networking_per_day(mode: str) -> int:
    return {"CRISIS": 8, "URGENT": 6, "STANDARD": 4, "STRATEGIC": 2}[mode]


def _sd_per_day(mode: str, leetcode_level: str | None) -> int:
    """System design only starts once user can reliably solve mediums."""
    if leetcode_level in ("fundamentals", "building"):
        return 0
    return {"CRISIS": 1, "URGENT": 1, "STANDARD": 1, "STRATEGIC": 2}.get(mode, 1)


# ── Public: initial plan targets ──────────────────────────────────────────────

def compute_initial_targets(
    days_left: int | None,
    days_since: int | None,
    leetcode_level: str | None,
    experience_band: str | None = None,
    resume_score: int | None = None,
    role: str | None = None,
    realistic_role: str | None = None,
) -> tuple[dict, str, str]:
    """
    Compute daily targets for the initial goal plan from profile signals.

    All params derive from the user profile — nothing is a fixed industry constant:
      experience_band   → sets screen_rate baseline
      resume_score      → adjusts screen_rate ±30%
      leetcode_level    → sets pass_rate + lc_goal factor
      realistic_role    → sets rounds estimate (FAANG vs startup)
      role              → sets lc_goal base (SWE vs MLE vs AI)
      days_left/since   → sets urgency mode and app spread

    Returns (targets_dict, mode_str, human_readable_reason).
    """
    mode = _mode_from_deadline(days_left, days_since)

    screen_rate  = _estimate_screen_rate(experience_band, resume_score)
    pass_rate    = _estimate_pass_rate(leetcode_level)
    rounds       = _estimate_rounds(realistic_role)
    lc_goal      = _estimate_lc_goal(role, experience_band, leetcode_level)

    pipeline_success_p = pass_rate ** rounds
    pipelines_needed   = math.ceil(1 / pipeline_success_p)
    remaining_apps     = math.ceil(pipelines_needed / screen_rate)
    effective_days     = max(1, days_left or 30)
    raw_apps           = math.ceil(remaining_apps / effective_days)
    apps_per_day       = min(_MAX_APPS_PER_DAY, max(_MIN_APPS_PER_DAY, raw_apps))

    lc  = _lc_per_day(days_left, leetcode_level, lc_goal)
    net = _networking_per_day(mode)
    sd  = _sd_per_day(mode, leetcode_level)

    horizon = min(days_left or _LC_HORIZON_DAYS, _LC_HORIZON_DAYS)
    reason = (
        f"Mode: {mode} | "
        f"Profile: {experience_band or 'mid'} band, {leetcode_level or 'standard'} LC, {rounds}-round target | "
        f"Screen rate: {screen_rate*100:.0f}% | Pass rate: {pass_rate*100:.0f}% | "
        f"{pipeline_success_p*100:.1f}% pipeline success → {pipelines_needed} screens → "
        f"{remaining_apps} apps → {apps_per_day}/day | "
        f"LC goal: {lc_goal} problems → {lc}/day over {horizon} days"
    )
    targets = {
        "applications":        apps_per_day,
        "networking_messages": net,
        "leetcode_problems":   lc,
        "system_design_sessions": sd,
    }
    return targets, mode, reason


# ── Internal: live recalibration funnel ───────────────────────────────────────

def _funnel_targets(
    base: dict,
    days_left: int | None,
    screen_rate: float,
    pass_rate_pct: float | None,
    signals: dict,
    active_pipelines: int = 0,
    rounds: int = 5,
) -> tuple[dict, str]:
    """
    Compute adjusted daily targets from live funnel data.

    screen_rate and pass_rate_pct come from real DB data when available.
    rounds comes from the belief state (profile-derived estimate).
    Overrides fire in priority order: burnout > interview_tomorrow > active_pipelines > leak cases.
    The LLM diagnosis in signals.diagnosis informs the override selection.
    """
    lc_base  = base.get("leetcode_problems", 2)
    net_base = base.get("networking_messages", 5)

    per_round = max(0.20, (pass_rate_pct or 50) / 100)
    conv_rate = max(0.03, screen_rate)

    pipeline_success_p = per_round ** rounds
    pipelines_needed   = math.ceil(1 / pipeline_success_p)

    remaining_pipelines = max(0, pipelines_needed - active_pipelines)
    remaining_apps      = math.ceil(remaining_pipelines / conv_rate)

    effective_days = max(1, days_left or 30)
    raw_apps_day   = math.ceil(remaining_apps / effective_days)
    apps_per_day   = min(_MAX_APPS_PER_DAY, max(_MIN_APPS_PER_DAY, raw_apps_day))

    prep_boost_lc = min(2, active_pipelines // 2)
    prep_boost_sd = 1 if active_pipelines >= 2 else 0

    # Pull LLM diagnosis to enrich the reason string
    diagnosis = signals.get("diagnosis") or {}
    diag_text = diagnosis.get("diagnosis", "")

    funnel_summary = (
        f"{per_round*100:.0f}% per-round × {rounds} rounds = {pipeline_success_p*100:.1f}% pipeline success → "
        f"need {pipelines_needed} screens, {active_pipelines} in flight → "
        f"{remaining_pipelines} more needed → {remaining_apps} apps → "
        f"{apps_per_day}/day over {days_left or '?'} days"
    )

    # ── Override 1: Burned out ───────────────────────────────────────────────
    if signals.get("burned_out"):
        reason = (
            f"Burned out (mood {signals['avg_mood']}/10, energy {signals['avg_energy']}/10). "
            f"{diag_text} Targets reduced to protect the search. | {funnel_summary}"
        )
        return {
            "applications":        max(_MIN_APPS_PER_DAY, apps_per_day // 3),
            "networking_messages": 2,
            "leetcode_problems":   1,
            "system_design_sessions": 0,
        }, reason

    # ── Override 2: Interview tomorrow ───────────────────────────────────────
    if signals.get("interviews_tomorrow", 0) > 0:
        topics = signals.get("interview_topics_tomorrow") or ["algorithms", "system design"]
        reason = (
            f"Interview tomorrow ({', '.join(topics)}) — everything pivots to prep. "
            f"| {funnel_summary}"
        )
        return {
            "applications":        max(_MIN_APPS_PER_DAY, apps_per_day // 4),
            "networking_messages": max(1, net_base // 3),
            "leetcode_problems":   lc_base + 2,
            "system_design_sessions": 2,
        }, reason

    # ── Active pipelines in flight → shift from applying to prep ─────────────
    if active_pipelines >= 2:
        reason = (
            f"{active_pipelines} active pipelines in flight — reduced new apps, boosted prep. "
            f"{diag_text} | {funnel_summary}"
        )
        return {
            "applications":        apps_per_day,
            "networking_messages": net_base,
            "leetcode_problems":   lc_base + prep_boost_lc,
            "system_design_sessions": 1 + prep_boost_sd,
        }, reason

    # ── Leak: LLM-diagnosed gap takes priority over rule checks ──────────────
    primary_gap = diagnosis.get("primary_gap")
    gap_conf    = diagnosis.get("confidence", "low")

    if primary_gap in ("resume", "volume") and gap_conf in ("medium", "high"):
        if conv_rate < 0.05 and signals.get("total_apps_7d", 0) > 20:
            reason = (
                f"Screen rate {conv_rate*100:.1f}% — {diag_text} "
                f"Networking boosted as parallel channel. | {funnel_summary}"
            )
            return {
                "applications":        apps_per_day,
                "networking_messages": net_base + 2,
                "leetcode_problems":   lc_base + prep_boost_lc,
                "system_design_sessions": 1 + prep_boost_sd,
            }, reason

    if primary_gap in ("technical_lc", "technical_sd", "behavioral") and gap_conf in ("medium", "high"):
        if signals.get("total_interviews_7d", 0) > 0:
            extra_lc = 2 if primary_gap == "technical_lc" else 1
            extra_sd = 2 if primary_gap == "technical_sd" else 1
            reason = (
                f"LLM diagnosis: {diag_text} "
                f"Cutting applications, shifting to targeted prep. | {funnel_summary}"
            )
            return {
                "applications":        max(_MIN_APPS_PER_DAY, apps_per_day // 2),
                "networking_messages": max(2, net_base // 2),
                "leetcode_problems":   lc_base + extra_lc + prep_boost_lc,
                "system_design_sessions": extra_sd + prep_boost_sd,
            }, reason

    # ── Leak: Low screen rate (fallback rule) ────────────────────────────────
    if conv_rate < 0.05 and signals.get("total_apps_7d", 0) > 20:
        reason = (
            f"Screen rate {conv_rate*100:.1f}% — resume or targeting broken. "
            f"| {funnel_summary}"
        )
        return {
            "applications":        apps_per_day,
            "networking_messages": net_base + 2,
            "leetcode_problems":   lc_base + prep_boost_lc,
            "system_design_sessions": 1 + prep_boost_sd,
        }, reason

    # ── Leak: Low pass rate (fallback rule) ──────────────────────────────────
    if (pass_rate_pct or 50) < 50 and signals.get("total_interviews_7d", 0) > 0:
        reason = (
            f"Pass rate {pass_rate_pct:.0f}% — pipeline success {pipeline_success_p*100:.1f}%. "
            f"Cutting apps, doubling prep. | {funnel_summary}"
        )
        return {
            "applications":        max(_MIN_APPS_PER_DAY, apps_per_day // 2),
            "networking_messages": max(2, net_base // 2),
            "leetcode_problems":   lc_base + 2 + prep_boost_lc,
            "system_design_sessions": 2 + prep_boost_sd,
        }, reason

    # ── Leak: No interviews in 14 days ───────────────────────────────────────
    if signals.get("no_interview_14d") and signals.get("total_apps_7d", 0) > 10:
        reason = (
            f"{signals.get('days_since_interview', '14+')} days without a phone screen. "
            f"Pushing volume + networking. | {funnel_summary}"
        )
        return {
            "applications":        min(_MAX_APPS_PER_DAY, apps_per_day + 3),
            "networking_messages": net_base + 3,
            "leetcode_problems":   lc_base + prep_boost_lc,
            "system_design_sessions": 1 + prep_boost_sd,
        }, reason

    # ── Default: on track ────────────────────────────────────────────────────
    reason = f"On track. {diag_text} | {funnel_summary}"
    return {
        "applications":        apps_per_day,
        "networking_messages": net_base,
        "leetcode_problems":   lc_base + prep_boost_lc,
        "system_design_sessions": 1 + prep_boost_sd,
    }, reason


# ── Public: weekly recalibration ─────────────────────────────────────────────

async def recalibrate_targets(user_id: str) -> dict:
    """Recompute funnel targets from real data and write back to goal_plan + belief_state."""
    from crisiscoach.db.supabase import get_client
    sb = get_client()

    # ── 1. Load goal plan ────────────────────────────────────────────────────
    goal_row = (
        sb.table("goal_plan")
        .select("id, goal_stratergy")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data

    if not goal_row:
        logger.info(f"[RECALIBRATOR] user={user_id} — no goal plan yet, skipping")
        return {"skipped": True, "reason": "no_goal_plan"}

    plan_id       = goal_row[0]["id"]
    goal_stratergy = goal_row[0].get("goal_stratergy") or {}
    base_targets   = goal_stratergy.get("daily_targets", {})

    # ── 2. Load user profile + belief state ──────────────────────────────────
    user_row = (
        sb.table("users")
        .select("search_start_date, runway_weeks, belief_state, leetcode_level")
        .eq("id", user_id)
        .single()
        .execute()
    ).data or {}

    from crisiscoach.db.belief_state import (
        read as read_belief, write as write_belief, bayesian_update
    )
    belief = read_belief(user_id, sb)
    experience_band = belief.get("experience_band")
    resume_score    = goal_stratergy.get("resume_score") or belief.get("resume_score")
    leetcode_level  = user_row.get("leetcode_level") or belief.get("estimated_lc_level")
    realistic_role  = (goal_stratergy.get("role_targets") or {}).get("realistic")
    rounds          = _estimate_rounds(realistic_role)

    today = date.today()
    deadline_candidates = []
    if user_row.get("runway_weeks") is not None:
        deadline_candidates.append(user_row["runway_weeks"] * 7)
    days_left = min(deadline_candidates) if deadline_candidates else None

    # ── 3. Real conversion rates from last 30 days ───────────────────────────
    cutoff_30d = (today - timedelta(days=30)).isoformat()

    logs_30d = (
        sb.table("daily_log")
        .select("apps_done, interviews_attended")
        .eq("user_id", user_id)
        .gte("date", cutoff_30d)
        .execute()
    ).data or []

    total_apps_30d       = sum(r.get("apps_done", 0) for r in logs_30d)
    total_interviews_30d = sum(r.get("interviews_attended", 0) for r in logs_30d)

    # When no data yet: fall back to profile-derived estimate (not hardcoded constant)
    observed_screen_rate = (
        total_interviews_30d / total_apps_30d
        if total_apps_30d > 0
        else _estimate_screen_rate(experience_band, resume_score)
    )

    interviews_30d = (
        sb.table("interviews")
        .select("status")
        .eq("user_id", user_id)
        .gte("date", cutoff_30d)
        .execute()
    ).data or []

    passed_30d    = sum(1 for r in interviews_30d if r.get("status") == "pass")
    total_tracked = len(interviews_30d)
    pass_rate_pct = (
        round(passed_30d / total_tracked * 100)
        if total_tracked > 0
        else None
    )

    # Bayesian-blend prior with observed (more data → trust data more)
    n_obs = total_apps_30d + total_tracked
    screen_rate = bayesian_update(
        prior=belief.get("estimated_screen_rate", _estimate_screen_rate(experience_band, resume_score)),
        observed=observed_screen_rate,
        n_obs=n_obs,
    )

    # ── 4. Active pipelines ──────────────────────────────────────────────────
    cutoff_14d = (today - timedelta(days=14)).isoformat()
    recent_interviews = (
        sb.table("interviews")
        .select("company, status")
        .eq("user_id", user_id)
        .gte("date", cutoff_14d)
        .execute()
    ).data or []
    companies_in_flight = {r["company"] for r in recent_interviews if r.get("company")}
    active_pipelines = len(companies_in_flight)

    # ── 5. Behavioral signals (includes LLM diagnosis) ───────────────────────
    signals = await analyze(user_id, sb)

    # ── 6. Compute new targets ───────────────────────────────────────────────
    new_targets, reason = _funnel_targets(
        base=base_targets,
        days_left=days_left,
        screen_rate=screen_rate,
        pass_rate_pct=pass_rate_pct,
        signals=signals,
        active_pipelines=active_pipelines,
        rounds=rounds,
    )

    # ── 7. Write goal_plan ───────────────────────────────────────────────────
    updated = {
        **goal_stratergy,
        "daily_targets": new_targets,
        "last_recalibration": {
            "date": today.isoformat(),
            "reason": reason,
            "funnel_snapshot": {
                "days_left":             days_left,
                "screen_rate_pct":       round(screen_rate * 100, 1),
                "pass_rate_pct":         pass_rate_pct,
                "total_apps_30d":        total_apps_30d,
                "total_interviews_30d":  total_interviews_30d,
                "active_pipelines":      active_pipelines,
                "rounds_estimate":       rounds,
            },
        },
    }
    sb.table("goal_plan").update({"goal_stratergy": updated}).eq("id", plan_id).execute()

    # ── 8. Update belief state with Bayesian rates + LLM diagnosis ───────────
    try:
        diagnosis     = signals.get("diagnosis") or {}
        belief_update = {
            "estimated_screen_rate": screen_rate,
            "estimated_rounds":      rounds,
            "data_points":           n_obs,
        }
        if pass_rate_pct is not None:
            updated_pr = bayesian_update(
                prior=belief.get("estimated_pass_rate", _estimate_pass_rate(leetcode_level)),
                observed=pass_rate_pct / 100,
                n_obs=total_tracked,
            )
            belief_update["estimated_pass_rate"] = updated_pr
        if diagnosis.get("primary_gap"):
            belief_update["primary_gap"]    = diagnosis["primary_gap"]
            belief_update["gap_confidence"] = diagnosis.get("confidence", "low")
            belief_update["diagnosis"]      = diagnosis.get("diagnosis")
            belief_update["top_actions"]    = diagnosis.get("top_actions", [])
        write_belief(user_id, belief_update, sb)
    except Exception as e:
        logger.warning(f"[RECALIBRATOR] belief state write failed: {e}")

    logger.info(
        f"[RECALIBRATOR] user={user_id} | days_left={days_left} | "
        f"screen={screen_rate*100:.1f}% pass={pass_rate_pct}% rounds={rounds} | {reason[:80]}"
    )
    return {"ok": True, "targets": new_targets, "reason": reason}
