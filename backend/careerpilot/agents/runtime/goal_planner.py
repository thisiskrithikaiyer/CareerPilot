"""Goal planner agent — builds a personalized 60-day job search strategy after intake."""
import json
import math
from datetime import date, timedelta
from langchain_core.messages import HumanMessage
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL
from careerpilot.orchestrator.state import State
from careerpilot.orchestrator.state_prompt import state_to_prompt
from careerpilot.prompts.loader import load_prompt

_EXTRACTION_PROMPT = """
Extract the goal plan from the assistant message below into this exact JSON schema.
Return ONLY valid JSON — no markdown, no explanation.

{
  "mode": "CRISIS | URGENT | STANDARD | STRATEGIC",
  "reasoning": "<1-2 sentences explaining why this mode was chosen, e.g. runway, search duration>",
  "resume_score": <int 1-10 or null>,
  "linkedin_score": <int 1-10 or null>,
  "experience_band": "junior | mid | senior | staff_plus",
  "role_targets": {
    "stretch": "<full role title including level, e.g. 'Senior Software Engineer'>",
    "realistic": "<full role title including level>",
    "safety": "<full role title including level>"
  },
  "daily_targets": {
    "applications": <int>,
    "networking_messages": <int>,
    "linkedin_connects": <int>,
    "leetcode_problems": <int>
  },
  "weekly_milestones": [
    {"week": "1-2", "goal": "<summary>"},
    {"week": "3-4", "goal": "<summary>"},
    {"week": "5-6", "goal": "<summary>"},
    {"week": "7-8", "goal": "<summary>"}
  ],
  "leetcode_tier": "fundamentals | building | standard | advanced",
  "technical_focus": "<one sentence summary of technical practice focus>",
  "suggested_info": "<one sentence about what additional info would sharpen the plan, or null if nothing meaningful is missing>"
}

Assistant message:
"""


# ── Level 4: Tool definitions ─────────────────────────────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "estimate_funnel_params",
            "description": (
                "Computes personalized funnel parameters from the user's profile: "
                "screen rate, per-round pass rate, rounds needed, and total LC problem goal. "
                "Call this FIRST (before presenting any numbers) once you have scored the resume "
                "and identified the experience band. Returns calibrated values specific to this person."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "experience_band": {
                        "type": "string",
                        "enum": ["junior", "mid", "senior", "staff_plus"],
                        "description": "Inferred from resume years of experience and most recent title",
                    },
                    "leetcode_level": {
                        "type": "string",
                        "enum": ["fundamentals", "building", "standard", "advanced"],
                        "description": "From intake chip selection",
                    },
                    "resume_score": {
                        "type": "integer",
                        "description": "Score you assigned (1-10), or omit if not yet scored",
                    },
                    "role": {
                        "type": "string",
                        "description": "SWE | MLE | AI Engineer | Data Engineer",
                    },
                    "target_role": {
                        "type": "string",
                        "description": "Realistic role target name, e.g. 'Senior Software Engineer at mid-size company'",
                    },
                },
                "required": ["experience_band", "leetcode_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weak_interview_topics",
            "description": (
                "Fetches the user's weakest interview topics from the last 30 days of interview records. "
                "Call this in REVISION MODE when the user has interview data. "
                "Use the results to prescribe specific targeted prep instead of generic advice."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_interview_profile",
            "description": (
                "Returns the typical interview process for a company or company tier: "
                "number of rounds, difficulty, timeline, and key focus areas. "
                "Call this when the user mentions a specific company or targets a specific tier."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_or_tier": {
                        "type": "string",
                        "description": "Company name (e.g. 'Google') or tier (e.g. 'FAANG', 'startup', 'mid-size')",
                    },
                },
                "required": ["company_or_tier"],
            },
        },
    },
]

# Company process lookup table — used by get_company_interview_profile
_COMPANY_PROFILES: dict[str, dict] = {
    "google":    {"rounds": 7, "difficulty": "hard",        "timeline_weeks": 6, "focus": ["algorithms", "system_design", "behavioral"]},
    "meta":      {"rounds": 6, "difficulty": "hard",        "timeline_weeks": 5, "focus": ["algorithms", "system_design", "behavioral"]},
    "amazon":    {"rounds": 5, "difficulty": "medium_hard", "timeline_weeks": 4, "focus": ["algorithms", "system_design", "leadership_principles"]},
    "microsoft": {"rounds": 5, "difficulty": "medium",      "timeline_weeks": 4, "focus": ["algorithms", "system_design", "behavioral"]},
    "apple":     {"rounds": 6, "difficulty": "hard",        "timeline_weeks": 6, "focus": ["algorithms", "system_design", "role_specific"]},
    "openai":    {"rounds": 5, "difficulty": "hard",        "timeline_weeks": 4, "focus": ["ml_fundamentals", "system_design", "research_discussion"]},
    "stripe":    {"rounds": 5, "difficulty": "hard",        "timeline_weeks": 4, "focus": ["algorithms", "system_design", "code_review"]},
    "startup":   {"rounds": 3, "difficulty": "medium",      "timeline_weeks": 2, "focus": ["algorithms", "take_home", "culture_fit"]},
    "mid_size":  {"rounds": 4, "difficulty": "medium",      "timeline_weeks": 3, "focus": ["algorithms", "system_design", "behavioral"]},
}


def _tool_estimate_funnel_params(args: dict, state: State) -> dict:
    from careerpilot.agents.background.target_recalibrator import (
        _estimate_screen_rate, _estimate_pass_rate, _estimate_rounds, _estimate_lc_goal,
    )
    band       = args.get("experience_band")
    lc_level   = args.get("leetcode_level") or state.get("leetcode_level")
    resume_score = args.get("resume_score")
    role       = args.get("role")
    target_role = args.get("target_role", "")

    sr      = _estimate_screen_rate(band, resume_score)
    pr      = _estimate_pass_rate(lc_level)
    rounds  = _estimate_rounds(target_role)
    lc_goal = _estimate_lc_goal(role, band, lc_level)

    pipeline_p       = pr ** rounds
    pipelines_needed = math.ceil(1 / pipeline_p)
    total_apps       = math.ceil(pipelines_needed / sr)

    return {
        "estimated_screen_rate_pct":  round(sr * 100, 1),
        "estimated_pass_rate_pct":    round(pr * 100, 1),
        "estimated_rounds":           rounds,
        "estimated_lc_goal":          lc_goal,
        "pipeline_success_pct":       round(pipeline_p * 100, 2),
        "pipelines_needed":           pipelines_needed,
        "total_apps_to_1_offer":      total_apps,
        "funnel_summary": (
            f"{round(pr*100)}% per-round × {rounds} rounds = {round(pipeline_p*100,1)}% pipeline success → "
            f"need {pipelines_needed} phone screens → {total_apps} total apps to 1 offer"
        ),
    }


def _tool_get_weak_topics(user_id: str) -> dict:
    try:
        from careerpilot.db.supabase import get_client
        sb = get_client()
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        rows = (
            sb.table("interviews")
            .select("topics, status")
            .eq("user_id", user_id)
            .gte("date", cutoff)
            .execute()
        ).data or []

        topic_stats: dict[str, dict] = {}
        for r in rows:
            for t in (r.get("topics") or []):
                topic_stats.setdefault(t, {"pass": 0, "fail": 0})
                if r.get("status") == "pass":
                    topic_stats[t]["pass"] += 1
                else:
                    topic_stats[t]["fail"] += 1

        weak = sorted(
            [
                {
                    "topic": t,
                    "pass_rate_pct": round(v["pass"] / (v["pass"] + v["fail"]) * 100),
                    "attempts": v["pass"] + v["fail"],
                }
                for t, v in topic_stats.items()
                if (v["pass"] + v["fail"]) > 0
            ],
            key=lambda x: x["pass_rate_pct"],
        )
        return {"weak_topics": weak[:5], "window": "last_30_days", "total_topics_seen": len(topic_stats)}
    except Exception as e:
        return {"error": str(e), "weak_topics": []}


def _tool_get_company_profile(company_or_tier: str) -> dict:
    key = company_or_tier.lower().strip()
    for name, profile in _COMPANY_PROFILES.items():
        if name in key or key in name:
            return {**profile, "matched": name}
    if any(w in key for w in ["faang", "big tech", "top tier", "top-tier"]):
        return {**_COMPANY_PROFILES["google"], "matched": "faang_tier"}
    if any(w in key for w in ["startup", "early", "seed", "series a", "series b"]):
        return {**_COMPANY_PROFILES["startup"], "matched": "startup"}
    return {**_COMPANY_PROFILES["mid_size"], "matched": "mid_size_default"}


def _handle_tool(name: str, args: dict, state: State) -> str:
    try:
        if name == "estimate_funnel_params":
            result = _tool_estimate_funnel_params(args, state)
        elif name == "get_weak_interview_topics":
            result = _tool_get_weak_topics(state.get("user_id", ""))
        elif name == "get_company_interview_profile":
            result = _tool_get_company_profile(args.get("company_or_tier", "unknown"))
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as e:
        result = {"error": str(e)}
    return json.dumps(result)


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system(state: State) -> str:
    base = load_prompt("goal_planner.txt")
    snippets = [state_to_prompt(state)]

    if state.get("resume_text"):
        snippets.append(f"\nRESUME TEXT:\n{state['resume_text']}")
    if state.get("linkedin_text"):
        snippets.append(f"\nLINKEDIN PROFILE TEXT:\n{state['linkedin_text']}")

    tracking = state.get("tracking_summary")

    # ── L3: Inject belief state so LLM has the system's current model ────────
    user_id = state.get("user_id")
    if user_id:
        try:
            from careerpilot.db.supabase import get_client
            from careerpilot.db.belief_state import read as read_belief
            belief = read_belief(user_id, get_client())
            if belief.get("last_updated"):
                b = belief
                snippets.append("\n--- BELIEF STATE (system's current model of your search) ---")
                snippets.append(f"Estimated screen rate: {round(b['estimated_screen_rate']*100, 1)}%")
                snippets.append(f"Estimated pass rate: {round(b['estimated_pass_rate']*100, 1)}%")
                snippets.append(f"Estimated rounds to offer: {b['estimated_rounds']}")
                snippets.append(f"Target LC problems: {b['estimated_lc_goal']}")
                snippets.append(f"Experience band: {b.get('experience_band') or 'not yet determined'}")
                if b.get("primary_gap"):
                    snippets.append(f"Primary gap (LLM-diagnosed): {b['primary_gap']} ({b['gap_confidence']} confidence)")
                    snippets.append(f"Diagnosis: {b['diagnosis']}")
                    if b.get("top_actions"):
                        snippets.append(f"Recommended actions: {' | '.join(b['top_actions'])}")
                snippets.append(f"Data points used: {b['data_points']} (apps + interviews seen)")
        except Exception as e:
            print(f"[GOAL_PLANNER] belief state read failed: {e}")

    # ── Computed baseline targets (initial plan only, not revision) ───────────
    if not (tracking or {}).get("revision_mode"):
        try:
            from careerpilot.agents.background.target_recalibrator import compute_initial_targets
            computed, mode, reason = compute_initial_targets(
                days_left=state.get("days_left"),
                days_since=state.get("days_since"),
                leetcode_level=state.get("leetcode_level"),
            )
            snippets.append(
                "\n--- BASELINE DAILY TARGETS (profile-derived — call estimate_funnel_params to refine) ---"
                f"\nMode: {mode}"
                f"\nApplications: {computed['applications']}/day"
                f"\nNetworking messages: {computed['networking_messages']}/day"
                f"\nLeetcode problems: {computed['leetcode_problems']}/day"
                f"\nSystem design sessions: {computed['system_design_sessions']}/day"
                f"\nTarget reasoning: {reason}"
            )
        except Exception as e:
            print(f"[GOAL_PLANNER] compute_initial_targets failed: {e}")

    if tracking and tracking.get("revision_mode"):
        t = tracking
        act = t.get("activity", {})
        dev = t.get("deviation", {})
        ts  = t.get("task_stats", {})

        snippets.append("\n--- REVISION DATA (pre-computed from DB — do not fabricate any number) ---")
        snippets.append("REVISION_MODE: true")
        snippets.append(f"Current day of search: Day {t.get('current_day')}")
        snippets.append(f"Avg mood: {t.get('avg_mood')}/10 | Avg energy: {t.get('avg_energy')}/10")

        if ts.get("completion_rate") is not None:
            snippets.append(f"Task completion: {ts['completion_rate']}% ({ts['completed']}/{ts['total']})")
        if ts.get("by_category"):
            snippets.append("By category: " + " | ".join(
                f"{cat}: {v['rate']}% ({v['completed']}/{v['total']})"
                for cat, v in ts["by_category"].items()
            ))

        if dev:
            for key, label in [("apps", "Apps"), ("networking", "Networking"), ("leetcode", "Leetcode")]:
                if key in dev and dev[key]["deviation_pct"] is not None:
                    d = dev[key]
                    snippets.append(f"{label}: {d['actual']} done (target {d['target']}, {d['deviation_pct']:+d}%)")
        snippets.append(f"System design sessions done: {act.get('total_system_design', 0)}")

        snippets.append(f"Interviews completed: {act.get('total_interviews_completed', 0)}")
        snippets.append(f"Interviews passed: {act.get('total_interviews_passed', 0)} | Failed: {act.get('total_interviews_failed', 0)}")
        if act.get("pass_rate") is not None:
            snippets.append(f"Interview pass rate: {act['pass_rate']}%")
        if act.get("top_interview_topics"):
            snippets.append(f"Top interview topics asked: {', '.join(act['top_interview_topics'])}")
        if act.get("days_since_interview") is not None:
            snippets.append(f"Days since last interview: {act['days_since_interview']}")
        if t.get("no_interview_rescore"):
            snippets.append("NO_INTERVIEW_FLAG: true — 14+ days with no interview. Resume/LinkedIn rescore required.")

        if t.get("recurring_blockers"):
            snippets.append(f"Recurring blockers: {', '.join(t['recurring_blockers'])}")

        if t.get("daily_log"):
            snippets.append("\nDaily activity log (oldest → newest):")
            for day in t["daily_log"]:
                snippets.append(
                    f"  {day['date']} | mood {day.get('mood','?')} energy {day.get('energy','?')} "
                    f"| apps {day.get('apps',0)} net {day.get('networking',0)} "
                    f"| lc {day.get('leetcode_done',0)} sd {day.get('system_design_done',0)} "
                    f"| interviews attended {day.get('interviews_attended',0)}"
                )

    return base + ("\n\nUser context:\n" + "\n".join(snippets) if snippets else "")


def _has_profile(state: State) -> bool:
    return bool(state.get("resume_text") or state.get("linkedin_text"))


def _save_flags(state: State) -> None:
    user_id = state.get("user_id")
    if not user_id:
        return
    updates = {}
    if state.get("days_since") is not None:
        search_start_date = date.today() - timedelta(days=state["days_since"])
        updates["search_start_date"] = search_start_date.isoformat()
    if not updates:
        return
    try:
        from careerpilot.db.supabase import get_client
        get_client().table("users").update(updates).eq("id", user_id).execute()
    except Exception:
        pass


def _extract_and_save_plan(user_id: str, response_text: str, revision_analytics: dict | None = None) -> str | None:
    """Extract structured JSON from the plan text, persist to goal_plan, and return the row id."""
    try:
        extraction = groq_complete(
            model=GROQ_MODEL,
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": _EXTRACTION_PROMPT + response_text}],
        )
        raw = extraction.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        plan_json = json.loads(raw)
    except Exception as e:
        print(f"[GOAL_PLANNER] JSON extraction failed: {e}")
        return None

    try:
        from careerpilot.db.supabase import get_client
        from careerpilot.agents.background.role_curriculum import get_curriculum, detect_role_type

        role_text = (plan_json.get("role_targets") or {}).get("realistic", "")
        role_type = detect_role_type(role_text)
        curriculum = get_curriculum(role_text)
        plan_json["role_type"] = role_type
        plan_json["curriculum"] = {
            "leetcode_topics": curriculum["leetcode_topics"],
            "system_design_concepts": curriculum["system_design_concepts"],
            "core_concepts": curriculum["core_concepts"],
        }

        row: dict = {
            "user_id": user_id,
            "date": date.today().isoformat(),
            "goal_stratergy": plan_json,
        }
        if revision_analytics:
            row["revision_analytics"] = revision_analytics
        result = get_client().table("goal_plan").insert(row).execute()
        plan_id: str | None = result.data[0]["id"] if result.data else None
        print(f"[GOAL_PLANNER] Plan saved — id={plan_id} mode={plan_json.get('mode')} role={role_type}")

        # ── L3: Write experience_band + resume_score to belief state ─────────
        try:
            from careerpilot.db.belief_state import write as write_belief
            sb = get_client()
            belief_update: dict = {}
            if plan_json.get("experience_band"):
                belief_update["experience_band"] = plan_json["experience_band"]
            if plan_json.get("resume_score") is not None:
                belief_update["resume_score"] = plan_json["resume_score"]
            if belief_update:
                write_belief(user_id, belief_update, sb)
        except Exception:
            pass

        return plan_id
    except Exception as e:
        print(f"[GOAL_PLANNER] DB insert failed: {e}")
        return None


async def run(state: State) -> dict:
    _save_flags(state)

    system = _build_system(state)
    history = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state["messages"]
    ]
    messages = [{"role": "system", "content": system}, *history]

    # ── L4: Agentic tool-calling loop (up to 3 rounds) ───────────────────────
    response_text: str | None = None
    try:
        for _ in range(3):
            resp = groq_complete(
                model=GROQ_MODEL,
                max_tokens=2048,
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
            )
            msg = resp.choices[0].message

            if not msg.tool_calls:
                response_text = msg.content
                break

            # Append assistant turn with tool calls
            assistant_entry: dict = {"role": "assistant", "content": msg.content or ""}
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
            messages.append(assistant_entry)

            # Execute each tool and append result
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_result = _handle_tool(tc.function.name, args, state)
                print(f"[GOAL_PLANNER] Tool: {tc.function.name} → {tool_result[:120]}")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result})

        if response_text is None:
            response_text = "Plan generation completed — tool results processed."

    except Exception as e:
        print(f"[GOAL_PLANNER] Tool calling failed ({e}), falling back to simple call")
        resp = groq_complete(
            model=GROQ_MODEL,
            max_tokens=2048,
            messages=[{"role": "system", "content": system}, *history],
        )
        response_text = resp.choices[0].message.content

    user_id  = state.get("user_id")
    tracking = state.get("tracking_summary") or {}

    last_human = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
    last_human_text = (last_human.content.strip().lower() if last_human else "")
    _COMMIT_SIGNALS = (
        "commit", "yes", "let's do it", "lets do it", "sounds good", "i'm in", "im in",
        "deal", "go for it", "agreed", "ok", "okay", "looks good", "that looks good",
        "great", "perfect", "sure", "works for me", "love it", "let's go", "lets go",
        "start", "begin", "ready", "i'm ready", "im ready", "do it", "absolutely",
        "definitely", "yep", "yup", "cool", "nice", "awesome",
    )
    committed = any(sig in last_human_text for sig in _COMMIT_SIGNALS)

    _PLAN_SIGNALS = ("week 1", "week 2", "daily target", "applications per day", "applications/day", "leetcode problems", "weekly milestone")
    is_plan_response = any(sig in response_text.lower() for sig in _PLAN_SIGNALS)

    saved_plan_id: str | None = None
    if user_id and is_plan_response:
        revision_analytics = {
            "activity":          tracking.get("activity"),
            "deviation":         tracking.get("deviation"),
            "task_stats":        tracking.get("task_stats"),
            "avg_mood":          tracking.get("avg_mood"),
            "avg_energy":        tracking.get("avg_energy"),
            "no_interview_rescore": tracking.get("no_interview_rescore"),
        } if tracking.get("revision_mode") else None
        saved_plan_id = _extract_and_save_plan(user_id, response_text, revision_analytics)

    if user_id and committed:
        try:
            from careerpilot.db.supabase import get_client
            sb = get_client()
            target_id = saved_plan_id
            if not target_id:
                latest = (
                    sb.table("goal_plan")
                    .select("id")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                ).data
                target_id = latest[0]["id"] if latest else None
            if target_id:
                sb.table("goal_plan").update({
                    "goal_committed_at":   date.today().isoformat(),
                    "next_revision_date":  (date.today() + timedelta(days=10)).isoformat(),
                }).eq("id", target_id).execute()
            sb.table("users").update({"phase": "active"}).eq("id", user_id).execute()
        except Exception as e:
            print(f"[GOAL_PLANNER] Commitment stamp failed: {e}")

        try:
            import asyncio
            from careerpilot.agents.background.target_recalibrator import recalibrate_targets
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(recalibrate_targets(user_id))
            else:
                loop.run_until_complete(recalibrate_targets(user_id))
        except Exception as e:
            print(f"[GOAL_PLANNER] Background tasks failed: {e}")

    new_phase = "active" if committed else state.get("phase", "goal_setup")

    # If we saved a plan, return a short greeting instead of the full plan dump.
    # The full text was only needed for extraction — the structured plan is in goal_plan table.
    if saved_plan_id and is_plan_response:
        display_response = (
            "Your 60-day plan is ready. Day 1 starts today — let's get to work. "
            "Ask me anything about your strategy, today's targets, or how to tackle any part of the search."
        )
    elif committed:
        display_response = (
            "Plan locked in. Let's go — I'm here every day to keep you on track."
        )
    else:
        display_response = response_text

    return {"response": display_response, "sources": [], "phase": new_phase}
