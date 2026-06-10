"""Planner agent — builds tomorrow's focused daily plan based on last 5 days of activity."""
import json
from datetime import date, timedelta
from careerpilot.utils.groq_client import groq_complete
from careerpilot.config import GROQ_MODEL

# Ordered leetcode topic curriculum — planner advances through this based on what's been done
LEETCODE_CURRICULUM = [
    {"topic": "Arrays & Hashing",       "problems": ["Two Sum", "Contains Duplicate", "Top K Frequent Elements"]},
    {"topic": "Two Pointers",           "problems": ["Valid Palindrome", "3Sum", "Container With Most Water"]},
    {"topic": "Sliding Window",         "problems": ["Best Time to Buy Stock", "Longest Substring Without Repeating", "Minimum Window Substring"]},
    {"topic": "Stack",                  "problems": ["Valid Parentheses", "Min Stack", "Daily Temperatures"]},
    {"topic": "Binary Search",          "problems": ["Binary Search", "Search in Rotated Sorted Array", "Find Minimum in Rotated Array"]},
    {"topic": "Linked List",            "problems": ["Reverse Linked List", "Merge Two Sorted Lists", "Linked List Cycle"]},
    {"topic": "Trees",                  "problems": ["Invert Binary Tree", "Maximum Depth of Binary Tree", "Lowest Common Ancestor"]},
    {"topic": "Tries",                  "problems": ["Implement Trie", "Design Add and Search Words", "Word Search II"]},
    {"topic": "Heap / Priority Queue",  "problems": ["Kth Largest Element", "Task Scheduler", "Find Median from Data Stream"]},
    {"topic": "Backtracking",           "problems": ["Combination Sum", "Word Search", "N-Queens"]},
    {"topic": "Graphs",                 "problems": ["Number of Islands", "Clone Graph", "Pacific Atlantic Water Flow"]},
    {"topic": "Dynamic Programming",    "problems": ["Climbing Stairs", "Coin Change", "Longest Common Subsequence"]},
    {"topic": "Greedy",                 "problems": ["Jump Game", "Gas Station", "Hand of Straights"]},
    {"topic": "Intervals",              "problems": ["Meeting Rooms", "Merge Intervals", "Non-overlapping Intervals"]},
    {"topic": "Bit Manipulation",       "problems": ["Number of 1 Bits", "Counting Bits", "Reverse Bits"]},
]

BEHAVIORAL_ROTATION = [
    "Conflict with a teammate — STAR format",
    "Biggest failure and what you learned",
    "Time you influenced without authority",
    "Most complex technical problem you solved",
    "Time you disagreed with your manager",
    "Delivered under a tight deadline",
    "Time you had to learn something fast",
    "Most impactful project you shipped",
    "How you handle ambiguous requirements",
    "Time you had to prioritize ruthlessly",
]


def _get_next_leetcode_topic(completed_topics: list[str]) -> dict:
    """Return the next unfinished topic from the curriculum."""
    completed_set = {t.lower() for t in completed_topics}
    for entry in LEETCODE_CURRICULUM:
        if entry["topic"].lower() not in completed_set:
            return entry
    # All done — cycle back to hardest topics
    return LEETCODE_CURRICULUM[-3]


def _get_behavioral_focus(day_index: int) -> str:
    return BEHAVIORAL_ROTATION[day_index % len(BEHAVIORAL_ROTATION)]


async def generate_plan(user_id: str) -> dict:
    from careerpilot.db.supabase import get_client
    sb = get_client()

    # Load user profile for goal targets
    profile = (sb.table("users").select("search_start_date").eq("id", user_id).single().execute()).data or {}
    days_since_start = 0
    if profile.get("search_start_date"):
        days_since_start = (date.today() - date.fromisoformat(profile["search_start_date"])).days

    # Last goal plan for targets
    goal_row = (
        sb.table("goal_plan")
        .select("goal_stratergy")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data
    goal_targets = {}
    if goal_row and goal_row[0].get("goal_stratergy"):
        goal_targets = goal_row[0]["goal_stratergy"].get("daily_targets", {})

    # Last 5 days of activity logs
    logs = (
        sb.table("daily_log")
        .select("date, apps_done, networking_done, leetcode_done, system_design_done, "
                "interviews_completed, interviews_passed, interviews_failed, interview_topics")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(5)
        .execute()
    ).data or []
    logs_asc = list(reversed(logs))

    # Determine completed leetcode topics from past plans (planner owns this, not daily_log)
    past_plans = (
        sb.table("plans")
        .select("plan_json")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(30)
        .execute()
    ).data or []
    completed_topics = list({
        p["plan_json"]["leetcode_topic"]
        for p in past_plans
        if p.get("plan_json") and p["plan_json"].get("leetcode_topic")
    })
    next_lc = _get_next_leetcode_topic(completed_topics)
    behavioral = _get_behavioral_focus(days_since_start)

    # Targets from goal plan, fallback to sensible defaults
    app_target = goal_targets.get("applications", 8)
    net_target = goal_targets.get("networking_messages", 5)
    lc_target = goal_targets.get("leetcode_problems", 2)

    # Build context for coach note generation
    last5_summary = json.dumps([
        {
            "date": r["date"],
            "apps": r.get("apps_done", 0),
            "networking": r.get("networking_done", 0),
            "leetcode": r.get("leetcode_done", 0),
            "interviews": r.get("interviews_completed", 0),
            "passed": r.get("interviews_passed", 0),
        }
        for r in logs_asc
    ])

    coach_resp = groq_complete(
        model=GROQ_MODEL,
        max_tokens=120,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a direct job-search coach. Write one sharp coaching note (2 sentences max) "
                    "based on the user's last 5 days. Call out the biggest gap. No fluff."
                ),
            },
            {"role": "user", "content": f"Last 5 days activity:\n{last5_summary}"},
        ],
    )
    coach_note = coach_resp.choices[0].message.content.strip()

    plan_json = {
        "date": (date.today() + timedelta(days=1)).isoformat(),
        "job_apps": app_target,
        "networking": net_target,
        "leetcode_problems": lc_target,
        "leetcode_topic": next_lc["topic"],
        "leetcode_suggested": next_lc["problems"][:lc_target],
        "behavioral_focus": behavioral,
        "system_design": 1 if days_since_start % 3 == 0 else 0,  # every 3 days
        "coach_note": coach_note,
    }

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    plan_row = sb.table("plans").insert({
        "user_id": user_id,
        "date": tomorrow,
        "coach_note": coach_note,
        "plan_json": plan_json,
    }).execute()
    plan_id = plan_row.data[0]["id"]

    # Merge daily plan into the latest goal_plan's goal_stratergy
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

    return {"plan_id": plan_id, "plan": plan_json}
