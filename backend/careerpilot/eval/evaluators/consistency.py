"""
Agent response consistency evaluator.

Runs the same input N times through the real graph and measures:
  - routing_agreement: % of runs that agree on the same intent
  - length_cv: coefficient of variation of response lengths (lower = more consistent)
  - keyword_pass_rate: how often the response passes keyword criteria
  - consistency_score: weighted composite (0-1)

A score >= 0.75 is considered passing.
"""
import asyncio
import statistics
from careerpilot.eval.evaluators.agent_response import run_case

PASS_THRESHOLD = 0.75

# Weights for the composite score
_W_ROUTING = 0.50
_W_LENGTH = 0.30
_W_KEYWORD = 0.20


async def run_consistency_check(case: dict, n_runs: int = 5) -> dict:
    """Run case n_runs times and return variance metrics."""
    tasks = [run_case(case) for _ in range(n_runs)]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    results = [r for r in raw if isinstance(r, dict) and not r.get("error")]

    if not results:
        return {
            "id": case.get("id", "?"),
            "n_attempted": n_runs,
            "n_succeeded": 0,
            "error": "all runs failed",
            "consistency_score": 0.0,
            "passed": False,
        }

    intents = [r["intent_routed"] for r in results]
    dominant_intent = max(set(intents), key=intents.count)
    routing_agreement = intents.count(dominant_intent) / len(intents)

    lengths = [len(r.get("response_snippet", "")) for r in results]
    mean_len = statistics.mean(lengths)
    length_cv = (statistics.stdev(lengths) / mean_len) if len(lengths) > 1 and mean_len > 0 else 0.0
    length_score = max(0.0, 1.0 - length_cv)

    keyword_pass_rate = sum(1 for r in results if r.get("passed")) / len(results)

    sim_scores = [r["similarity"]["avg_similarity"] for r in results]
    sim_stdev = statistics.stdev(sim_scores) if len(sim_scores) > 1 else 0.0

    consistency_score = round(
        _W_ROUTING * routing_agreement
        + _W_LENGTH * length_score
        + _W_KEYWORD * keyword_pass_rate,
        3,
    )

    return {
        "id": case.get("id", "?"),
        "n_attempted": n_runs,
        "n_succeeded": len(results),
        "dominant_intent": dominant_intent,
        "routing_agreement": round(routing_agreement, 3),
        "length_cv": round(length_cv, 3),
        "length_mean": round(mean_len, 1),
        "sim_stdev": round(sim_stdev, 2),
        "keyword_pass_rate": round(keyword_pass_rate, 3),
        "consistency_score": consistency_score,
        "passed": consistency_score >= PASS_THRESHOLD,
    }


async def run_consistency_suite(cases: list[dict], n_runs: int = 5) -> dict:
    """Check consistency for each case. Returns summary + per-case results."""
    results = []
    for case in cases:
        result = await run_consistency_check(case, n_runs)
        results.append(result)

    if not results:
        return {"results": [], "avg_consistency": 0.0, "pass_rate": 0.0}

    avg_consistency = round(
        sum(r.get("consistency_score", 0) for r in results) / len(results), 3
    )
    pass_rate = round(
        sum(1 for r in results if r.get("passed")) / len(results), 3
    )

    return {
        "n_runs_per_case": n_runs,
        "total_cases": len(results),
        "avg_consistency": avg_consistency,
        "pass_rate": pass_rate,
        "results": results,
    }
