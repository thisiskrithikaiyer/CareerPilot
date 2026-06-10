"""Evaluates whether generated plans are specific and appropriately sized."""
from __future__ import annotations


GENERIC_PHRASES = [
    "update your resume",
    "network with people",
    "apply to jobs",
    "practice interviewing",
    "take care of yourself",
]


def score_plan(tasks: list[dict], profile: dict) -> dict:
    """
    Returns a score dict:
      - specificity_score: 0-1 (fraction of tasks that aren't generic)
      - count_score: 0-1 (task count within expected range)
      - wellness_included: bool (required if mood < 5 or energy < 5)
    """
    if not tasks:
        return {"specificity_score": 0.0, "count_score": 0.0, "wellness_included": False, "passed": False}

    generic_count = sum(
        1 for t in tasks
        if any(phrase in t.get("title", "").lower() for phrase in GENERIC_PHRASES)
    )
    specificity_score = 1.0 - (generic_count / len(tasks))

    count = len(tasks)
    count_score = 1.0 if 3 <= count <= 6 else (0.5 if count in (2, 7) else 0.0)

    mood = profile.get("mood_score", 10)
    energy = profile.get("energy_score", 10)
    needs_wellness = mood < 5 or energy < 5
    has_wellness = any(t.get("category") == "wellness" for t in tasks)
    wellness_ok = has_wellness if needs_wellness else True

    passed = specificity_score >= 0.7 and count_score >= 0.5 and wellness_ok
    return {
        "specificity_score": round(specificity_score, 2),
        "count_score": count_score,
        "wellness_included": has_wellness,
        "passed": passed,
    }
