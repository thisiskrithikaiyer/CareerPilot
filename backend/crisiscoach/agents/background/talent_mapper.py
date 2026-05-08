"""Talent mapper — silently builds a scored skill map from all available signals.

Sources read:
  - users.resume_text, users.linkedin_text
  - users.tracking_skills (self-reported)
  - goal_plan.goal_stratergy.role_targets (target roles)
  - daily_log.interview_topics (what was actually asked in interviews)
  - checkins.wins (skill mentions from daily check-ins)

Output written to users.talent_map:
  {
    "<skill>": {
      "score": 1-10,
      "relevance": "high | medium | low",
      "evidence": ["resume", "linkedin", "interview", "self-reported", "checkin"]
    },
    ...
  }
"""
import json
from crisiscoach.utils.groq_client import groq_complete
from crisiscoach.config import GROQ_MODEL

_SCORE_PROMPT = """
You are a technical skills tracker. Score each skill based primarily on demonstrated activity — not just what's on a resume.

Return ONLY valid JSON — no markdown, no explanation.

Schema:
{
  "<skill_name>": {
    "score": <int 1-10>,
    "relevance": "high | medium | low",
    "evidence": ["resume" | "linkedin" | "interview" | "log" | "conversation" | "self-reported"]
  }
}

Scoring rules (activity is primary — resume is baseline only):
- score 1-2: on resume/LinkedIn only, no recent activity
- score 3-4: self-reported or mentioned in chat, no logged practice
- score 5-6: moderate logged activity (e.g. 10-30 leetcode problems, 2-4 system design sessions)
- score 7-8: strong logged activity (30+ problems or 5+ sessions) OR topic appeared in a PASSED interview
- score 9-10: topic appeared in multiple PASSED interviews AND strong logged practice
- FAILED interview topics: cap score at 5 regardless of other signals — exposure without demonstrated competency
- Quality matters: 100 easy array problems < 20 medium DP problems for interview readiness
- System design sessions count more per unit than leetcode easy problems
- relevance = high if skill appears in their target role requirements
- Only include skills relevant to software engineering / ML / data roles
- Do not fabricate skills not present in the signals

Candidate signals:
"""


async def _fetch_signals(sb, user_id: str) -> dict:
    """Pull all skill signals from the DB and conversation history for this user."""
    profile = (
        sb.table("users")
        .select("resume_text, linkedin_text, tracking_skills")
        .eq("id", user_id)
        .single()
        .execute()
    ).data or {}

    # Latest committed goal plan → target roles
    goal_row = (
        sb.table("goal_plan")
        .select("goal_stratergy")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    role_targets = {}
    if goal_row:
        strategy = goal_row[0].get("goal_stratergy") or {}
        role_targets = strategy.get("role_targets", {})

    # Activity counts from daily logs (last 60 entries)
    log_rows = (
        sb.table("daily_log")
        .select("leetcode_done, system_design_done")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(60)
        .execute()
    ).data or []
    total_leetcode = sum(r.get("leetcode_done") or 0 for r in log_rows)
    total_system_design = sum(r.get("system_design_done") or 0 for r in log_rows)

    # Interview details — topics and outcomes from interviews table
    interview_rows = (
        sb.table("interviews")
        .select("topics, status, stage, what_went_wrong")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(50)
        .execute()
    ).data or []
    topics_passed = list({t for r in interview_rows if r.get("status") == "pass" for t in (r.get("topics") or [])})
    topics_failed = list({t for r in interview_rows if r.get("status") == "fail" for t in (r.get("topics") or [])})

    # Wins from checkins (last 20)
    checkin_rows = (
        sb.table("checkins")
        .select("wins")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    ).data or []
    checkin_wins = [w for r in checkin_rows for w in (r.get("wins") or [])]

    # Semantic scan of conversation history for skill signals
    conversation_signals: list[str] = []
    try:
        from crisiscoach.db.message_store import query_skill_signals
        conversation_signals = await query_skill_signals(user_id, n_per_query=5)
    except Exception as e:
        print(f"[TALENT_MAPPER] Conversation scan failed: {e}")

    return {
        "resume_text": (profile.get("resume_text") or "")[:3000],
        "linkedin_text": (profile.get("linkedin_text") or "")[:1000],
        "tracking_skills": profile.get("tracking_skills") or {},
        "role_targets": role_targets,
        "topics_passed": topics_passed,
        "topics_failed": topics_failed,
        "total_leetcode": total_leetcode,
        "total_system_design": total_system_design,
        "checkin_wins": checkin_wins[:20],
        "conversation_signals": conversation_signals[:20],
    }


def _build_signals_block(signals: dict) -> str:
    parts = []
    if signals["resume_text"]:
        parts.append(f"RESUME:\n{signals['resume_text']}")
    if signals["linkedin_text"]:
        parts.append(f"LINKEDIN:\n{signals['linkedin_text']}")
    if signals["role_targets"]:
        roles = ", ".join(f"{k}: {v}" for k, v in signals["role_targets"].items() if v)
        parts.append(f"TARGET ROLES: {roles}")
    if signals["topics_passed"]:
        parts.append(f"INTERVIEW TOPICS PASSED: {', '.join(signals['topics_passed'])}")
    if signals["topics_failed"]:
        parts.append(f"INTERVIEW TOPICS FAILED: {', '.join(signals['topics_failed'])}")
    if signals["total_leetcode"]:
        parts.append(f"LEETCODE PROBLEMS SOLVED (last 60 days): {signals['total_leetcode']}")
    if signals["total_system_design"]:
        parts.append(f"SYSTEM DESIGN SESSIONS COMPLETED (last 60 days): {signals['total_system_design']}")
    if signals["checkin_wins"]:
        parts.append(f"CHECKIN WINS (skill signals): {'; '.join(signals['checkin_wins'][:10])}")
    if signals["tracking_skills"]:
        reported = ", ".join(f"{k}: {v}" for k, v in signals["tracking_skills"].items())
        parts.append(f"SELF-REPORTED SKILLS: {reported}")
    if signals.get("conversation_signals"):
        parts.append(
            "CONVERSATION SIGNALS (skill-relevant messages from chat history):\n"
            + "\n".join(f"- {s}" for s in signals["conversation_signals"])
        )
    return "\n\n".join(parts)


async def map_talent(user_id: str, resume_text: str = "", linkedin_summary: str = "") -> dict:
    """
    Build a scored skill map from all available signals and persist to users.talent_map.
    resume_text / linkedin_summary can be passed directly (e.g. on profile upload)
    or left empty to fetch from DB.
    """
    from crisiscoach.db.supabase import get_client
    sb = get_client()

    signals = await _fetch_signals(sb, user_id)

    # Allow caller to override with freshly uploaded text
    if resume_text:
        signals["resume_text"] = resume_text[:3000]
    if linkedin_summary:
        signals["linkedin_text"] = linkedin_summary[:1000]

    if not signals["resume_text"] and not signals["linkedin_text"]:
        return {}

    signals_block = _build_signals_block(signals)

    resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[
            {"role": "user", "content": _SCORE_PROMPT + signals_block},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    talent_map = json.loads(raw)

    sb.table("users").update({"talent_map": talent_map}).eq("id", user_id).execute()
    print(f"[TALENT_MAPPER] Scored {len(talent_map)} skills for user {user_id}")

    return talent_map
