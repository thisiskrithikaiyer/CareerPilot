"""
Signal Analyzer — reads all user data, computes raw signals, then asks an LLM
to diagnose the primary gap and recommend specific actions.

Output: raw signals dict + `diagnosis` key with LLM assessment.
Feeds into: plan_prioritizer (daily plan), target_recalibrator (belief state update).
"""
import json
from datetime import date, timedelta

from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL

_DIAGNOSIS_SYSTEM = """You are a job search analyst. Given the signals below, identify the single most impactful gap blocking this person's search.

Output ONLY valid JSON — no explanation, no markdown.

{
  "primary_gap": "resume | volume | technical_lc | technical_sd | behavioral | networking | burnout | on_track",
  "confidence": "low | medium | high",
  "diagnosis": "<1 sentence: what is broken and the specific evidence for it>",
  "top_actions": ["<concrete action 1 for today>", "<concrete action 2 for today>"]
}

Gap definitions:
- resume: applying but not getting screens (screen rate < 5% with 20+ apps)
- volume: not applying enough — way below target
- technical_lc: failing algorithm / coding rounds (failed_topics includes arrays/trees/dp/graphs)
- technical_sd: failing system design rounds specifically
- behavioral: failing behavioral / culture fit rounds
- networking: low referral activity, relying only on cold apply
- burnout: mood/energy chronically low, affecting output
- on_track: no significant gap detected
"""


def _diagnose(signals: dict) -> dict:
    """LLM reads raw signals and identifies the primary gap with specific evidence."""
    try:
        # Only diagnose when there is enough signal to reason from
        has_data = (
            signals.get("total_apps_7d", 0) >= 5
            or signals.get("total_interviews_7d", 0) >= 1
            or signals.get("burned_out")
        )
        if not has_data:
            return {
                "primary_gap": None,
                "confidence": "low",
                "diagnosis": "Insufficient data — fewer than 5 apps and no interviews yet.",
                "top_actions": ["Send first batch of applications", "Start leetcode streak today"],
            }

        ctx = (
            f"Apps sent (7d): {signals['total_apps_7d']} vs target {signals['app_target']}/day\n"
            f"Interviews (7d): {signals['total_interviews_7d']}\n"
            f"Screen rate: {round(signals['total_interviews_7d'] / max(signals['total_apps_7d'], 1) * 100, 1)}%\n"
            f"Interview pass rate: {signals.get('pass_rate', 'no data')}%\n"
            f"Failed interview topics: {', '.join(signals.get('failed_topics', [])) or 'none recorded'}\n"
            f"Days since last interview: {signals.get('days_since_interview', 'unknown')}\n"
            f"Burnout rate: {signals['burnout_rate']}/10 | Low energy days: {signals['low_energy_days']}\n"
            f"Resume score: {signals.get('resume_score', 'unknown')}/10\n"
            f"LinkedIn score: {signals.get('linkedin_score', 'unknown')}/10\n"
            f"Leetcode tier: {signals.get('leetcode_tier', 'unknown')}\n"
            f"Too many apps, zero callbacks: {signals['too_many_apps_no_callbacks']}\n"
            f"No interview in 14 days: {signals['no_interview_14d']}\n"
            f"Interview failing (pass < 50%): {signals['interview_failing']}"
        )
        resp = groq_complete(
            model=GROQ_MODEL,
            max_tokens=256,
            temperature=0,
            messages=[
                {"role": "system", "content": _DIAGNOSIS_SYSTEM},
                {"role": "user", "content": ctx},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception:
        return _rule_based_diagnosis(signals)


def _rule_based_diagnosis(signals: dict) -> dict:
    """Deterministic fallback when LLM is unavailable."""
    if signals.get("burned_out"):
        return {
            "primary_gap": "burnout",
            "confidence": "high",
            "diagnosis": f"Avg mood {signals['avg_mood']}/10 and energy {signals['avg_energy']}/10 over 7 days — sustainable pace is broken.",
            "top_actions": ["Cut daily targets by 50% today", "Take one full rest day this week"],
        }
    if signals.get("too_many_apps_no_callbacks"):
        return {
            "primary_gap": "resume",
            "confidence": "high",
            "diagnosis": f"{signals['total_apps_7d']} apps with zero callbacks — resume or targeting is broken.",
            "top_actions": ["Audit top 3 ATS keywords against job descriptions", "Narrow target list to roles with 80%+ match"],
        }
    if signals.get("interview_failing"):
        failed = signals.get("failed_topics", [])
        gap = "technical_sd" if any("design" in t.lower() for t in failed) else "technical_lc"
        return {
            "primary_gap": gap,
            "confidence": "medium",
            "diagnosis": f"Pass rate {signals['pass_rate']}% — failing on: {', '.join(failed) or 'unrecorded topics'}.",
            "top_actions": ["Add 1hr focused system design practice today", "Do a mock interview this week"],
        }
    if signals.get("no_interview_14d") and signals.get("total_apps_7d", 0) > 10:
        return {
            "primary_gap": "resume",
            "confidence": "medium",
            "diagnosis": f"{signals.get('days_since_interview', '14+')} days without a phone screen despite active applying.",
            "top_actions": ["Request a resume review from a peer or coach", "Apply only to roles where you meet 80%+ of requirements"],
        }
    return {
        "primary_gap": "on_track",
        "confidence": "medium",
        "diagnosis": "No major gap detected from current data.",
        "top_actions": ["Maintain current pace", "Focus on quality of applications over volume"],
    }


async def analyze(user_id: str, sb) -> dict:
    today = date.today()

    # ── Last 7 days of checkins ───────────────────────────────────────────────
    checkins = (
        sb.table("checkins")
        .select("mood_score, energy_score, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(7)
        .execute()
    ).data or []

    avg_mood = round(sum(c["mood_score"] for c in checkins) / len(checkins), 1) if checkins else 5.0
    avg_energy = round(sum(c["energy_score"] for c in checkins) / len(checkins), 1) if checkins else 5.0
    burnout_rate = max(0, round((10 - avg_mood + 10 - avg_energy) / 2, 1))
    low_energy_days = sum(1 for c in checkins if c["energy_score"] <= 4)

    # ── Last 7 days of activity logs ──────────────────────────────────────────
    logs = (
        sb.table("daily_log")
        .select("date, apps_done, networking_done, leetcode_done, system_design_done, interviews_attended")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(7)
        .execute()
    ).data or []

    total_apps = sum(r.get("apps_done", 0) for r in logs)
    total_interviews = sum(r.get("interviews_attended", 0) for r in logs)

    # ── Interview pass/fail + topics ──────────────────────────────────────────
    cutoff_7d = (today - timedelta(days=7)).isoformat()
    interview_rows = (
        sb.table("interviews")
        .select("status, topics")
        .eq("user_id", user_id)
        .gte("date", cutoff_7d)
        .execute()
    ).data or []
    total_passed = sum(1 for r in interview_rows if r.get("status") == "pass")
    total_failed = sum(1 for r in interview_rows if r.get("status") == "fail")
    pass_rate = (
        round(total_passed / (total_passed + total_failed) * 100)
        if (total_passed + total_failed) > 0 else None
    )
    failed_topics = [t for r in interview_rows if r.get("status") == "fail" for t in (r.get("topics") or [])]

    # ── Days since last interview attended ────────────────────────────────────
    days_since_interview = None
    for r in logs:
        if r.get("interviews_attended", 0) > 0:
            days_since_interview = (today - date.fromisoformat(r["date"])).days
            break

    # ── Interview tomorrow ────────────────────────────────────────────────────
    tomorrow = (today + timedelta(days=1)).isoformat()
    tomorrow_interviews = (
        sb.table("interviews")
        .select("company, topics")
        .eq("user_id", user_id)
        .eq("date", tomorrow)
        .execute()
    ).data or []
    interviews_tomorrow = len(tomorrow_interviews)
    interview_topics_tomorrow = [t for r in tomorrow_interviews for t in (r.get("topics") or [])]

    # ── Goal plan targets ─────────────────────────────────────────────────────
    goal_row = (
        sb.table("goal_plan")
        .select("goal_stratergy")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    goal = (goal_row[0].get("goal_stratergy") or {}) if goal_row else {}
    daily_targets = goal.get("daily_targets", {})
    app_target = daily_targets.get("applications", 8)
    net_target = daily_targets.get("networking_messages", 5)
    lc_target = daily_targets.get("leetcode_problems", 2)
    resume_score = goal.get("resume_score")
    linkedin_score = goal.get("linkedin_score")
    leetcode_tier = goal.get("leetcode_tier", "standard")

    # ── Derived boolean signals ───────────────────────────────────────────────
    too_many_apps_no_callbacks = total_apps >= (app_target * 5) and total_interviews == 0
    interview_failing = pass_rate is not None and pass_rate < 50
    no_interview_14d = days_since_interview is None or days_since_interview >= 14
    resume_weak = resume_score is not None and resume_score < 6
    linkedin_weak = linkedin_score is not None and linkedin_score < 6
    burned_out = burnout_rate >= 6 or low_energy_days >= 3

    signals = {
        "avg_mood": avg_mood,
        "avg_energy": avg_energy,
        "burnout_rate": burnout_rate,
        "burned_out": burned_out,
        "low_energy_days": low_energy_days,
        "total_apps_7d": total_apps,
        "total_interviews_7d": total_interviews,
        "pass_rate": pass_rate,
        "days_since_interview": days_since_interview,
        "failed_topics": list(set(failed_topics))[:5],
        "interviews_tomorrow": interviews_tomorrow,
        "interview_topics_tomorrow": interview_topics_tomorrow,
        "too_many_apps_no_callbacks": too_many_apps_no_callbacks,
        "interview_failing": interview_failing,
        "no_interview_14d": no_interview_14d,
        "resume_weak": resume_weak,
        "linkedin_weak": linkedin_weak,
        "app_target": app_target,
        "net_target": net_target,
        "lc_target": lc_target,
        "leetcode_tier": leetcode_tier,
        "resume_score": resume_score,
        "linkedin_score": linkedin_score,
    }

    # ── LLM diagnosis (non-blocking — falls back to rule-based) ──────────────
    signals["diagnosis"] = _diagnose(signals)

    return signals
