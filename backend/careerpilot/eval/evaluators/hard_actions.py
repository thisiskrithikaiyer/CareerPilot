"""
Hard evaluators — deterministic, exact-match product guarantees.

Unlike the similarity / LLM-judge evals, these assert exact behavior of the
product's write paths:
  1. progress extraction  — chat check-in → exact structured fields
  2. task close           — "close the X task" → exact plan task key
  3. next-day plan        — completed work → exact carryover / target math

(2) and (3) are pure functions: zero LLM calls, fully reproducible.
(1) calls the live model but is scored with exact assertions, not similarity.
"""
import json
from pathlib import Path

DATASETS_DIR = Path(__file__).parent.parent / "datasets"


def _load(name: str):
    with open(DATASETS_DIR / name) as f:
        return json.load(f)


# ── 1. Progress extraction (LLM, exact assertions) ───────────────────────────

def _check_extraction(expected: dict, got: dict) -> list[dict]:
    from careerpilot.agents.runtime.progress_actions import has_progress

    checks = []
    for key, want in expected.items():
        if key == "close_tasks_contains":
            ok = any(want.lower() in t.lower() for t in got.get("close_tasks", []))
            checks.append({"check": f"close_tasks contains '{want}'", "passed": ok,
                           "got": got.get("close_tasks", [])})
        elif key == "wins_nonempty":
            ok = bool(got.get("wins")) == want
            checks.append({"check": "wins nonempty", "passed": ok, "got": got.get("wins", [])})
        elif key == "blockers_nonempty":
            ok = bool(got.get("blockers")) == want
            checks.append({"check": "blockers nonempty", "passed": ok, "got": got.get("blockers", [])})
        elif key == "no_progress":
            ok = (not has_progress(got)) == want
            checks.append({"check": "no progress extracted", "passed": ok, "got": got})
        else:
            ok = got.get(key) == want
            checks.append({"check": f"{key} == {want!r}", "passed": ok, "got": got.get(key)})
    return checks


def eval_progress_extraction() -> dict:
    from careerpilot.agents.runtime.progress_actions import extract_progress

    cases = _load("progress_extraction_golden.json")
    results = []
    for case in cases:
        try:
            got = extract_progress(case["input"])
            checks = _check_extraction(case["expected"], got)
            passed = all(c["passed"] for c in checks)
            results.append({"id": case["id"], "passed": passed, "checks": checks})
        except Exception as e:
            results.append({"id": case["id"], "passed": False, "error": str(e)})
    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 4) if results else 0,
        "results": results,
    }


# ── 2. Task close matching (pure, no LLM) ─────────────────────────────────────

def eval_task_close() -> dict:
    from careerpilot.agents.runtime.progress_actions import match_task

    data = _load("task_close_golden.json")
    schedule = data["schedule"]
    results = []
    for case in data["cases"]:
        try:
            hit = match_task(case["request"], schedule, case.get("task_status"))
            got_key = hit[0] if hit else None
            passed = got_key == case["expected_key"]
            results.append({
                "id": case["id"],
                "passed": passed,
                "expected": case["expected_key"],
                "got": got_key,
                "matched_label": hit[1] if hit else None,
            })
        except Exception as e:
            results.append({"id": case["id"], "passed": False, "error": str(e)})
    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 4) if results else 0,
        "results": results,
    }


# ── 3. Next-day plan carryover (pure, no LLM) ─────────────────────────────────

def _check_carryover(expected: dict, carry: dict, adjusted: dict) -> list[dict]:
    checks = []
    for key, want in expected.items():
        if key == "carryover_contains":
            ok = any(want.lower() in t.lower() for t in carry.get("carryover_tasks", []))
            checks.append({"check": f"carryover contains '{want}'", "passed": ok,
                           "got": carry.get("carryover_tasks", [])})
        elif key == "carryover_not_contains":
            ok = not any(want.lower() in t.lower() for t in carry.get("carryover_tasks", []))
            checks.append({"check": f"carryover excludes '{want}'", "passed": ok,
                           "got": carry.get("carryover_tasks", [])})
        elif key == "carryover_empty":
            ok = (len(carry.get("carryover_tasks", [])) == 0) == want
            checks.append({"check": "carryover empty", "passed": ok,
                           "got": carry.get("carryover_tasks", [])})
        elif key == "adjusted_job_apps":
            ok = adjusted.get("job_apps") == want
            checks.append({"check": f"adjusted job_apps == {want}", "passed": ok,
                           "got": adjusted.get("job_apps")})
        else:
            ok = carry.get(key) == want
            checks.append({"check": f"{key} == {want!r}", "passed": ok, "got": carry.get(key)})
    return checks


def eval_next_day_plan() -> dict:
    from careerpilot.agents.background.carryover import compute_carryover, adjust_targets_for_carryover

    cases = _load("next_day_plan_golden.json")
    results = []
    for case in cases:
        try:
            carry = compute_carryover(
                case.get("prev_plan_json"),
                case.get("prev_schedule"),
                case.get("prev_log"),
            )
            base_targets = {"job_apps": (case.get("prev_plan_json") or {}).get("job_apps", 8)}
            adjusted = adjust_targets_for_carryover(base_targets, carry)
            checks = _check_carryover(case["expected"], carry, adjusted)
            passed = all(c["passed"] for c in checks)
            results.append({"id": case["id"], "passed": passed, "checks": checks})
        except Exception as e:
            results.append({"id": case["id"], "passed": False, "error": str(e)})
    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 4) if results else 0,
        "results": results,
    }
