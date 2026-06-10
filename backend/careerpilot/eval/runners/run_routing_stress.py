"""
Routing stress-test runner — tests the supervisor on 60 edge cases designed to surface
ambiguous inputs, emotional escalations, topic switches, and false-positive traps.

Usage:
    python -m careerpilot.eval.runners.run_routing_stress
    python -m careerpilot.eval.runners.run_routing_stress --filter mental_health
    python -m careerpilot.eval.runners.run_routing_stress --save
"""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DATASETS_DIR = Path(__file__).parent.parent / "datasets"
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def load_stress_cases(intent_filter: str | None = None) -> list[dict]:
    path = DATASETS_DIR / "routing_stress_golden.json"
    cases = json.loads(path.read_text())
    if intent_filter:
        cases = [c for c in cases if c.get("expected_intent") == intent_filter]
    return cases


def run_stress_eval(cases: list[dict]) -> dict:
    from careerpilot.eval.evaluators.routing_accuracy import score_routing
    routing_cases = [
        {
            "id": c["id"],
            "input": c["input"],
            "expected_intent": c["expected_intent"],
            "phase": c.get("phase", "active"),
        }
        for c in cases
    ]
    return score_routing(routing_cases)


def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def print_results(results: dict, cases: list[dict]) -> None:
    acc = results["accuracy"]
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  ROUTING STRESS TEST                                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  {_bar(acc)}  {acc:.1%}  ({results['correct']}/{results['total']})\n")

    # Per-intent breakdown
    by_intent: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    note_map = {c["id"]: c.get("note", "") for c in cases}

    for r in results["results"]:
        expected = r["expected"]
        by_intent[expected]["total"] += 1
        if r["correct"]:
            by_intent[expected]["correct"] += 1

    print("  Per-intent accuracy:")
    for intent, counts in sorted(by_intent.items()):
        intent_acc = counts["correct"] / counts["total"] if counts["total"] else 0
        bar = _bar(intent_acc, 12)
        print(f"    {intent:<18} {bar}  {intent_acc:.1%}  ({counts['correct']}/{counts['total']})")

    # Failures
    failures = [r for r in results["results"] if not r["correct"]]
    if failures:
        print(f"\n  ✗ Failures ({len(failures)}):")
        for f in failures:
            note = note_map.get(f["id"], "")
            print(f"    [{f['id']}] expected={f['expected']} got={f['predicted']}")
            print(f"           note: {note}")
            print(f"           reason: {f.get('reason', '')[:80]}")
    else:
        print("\n  ✓ All cases passed!")

    # Error analysis — what intents are being confused
    confusions: Counter = Counter()
    for f in failures:
        confusions[(f["expected"], f["predicted"])] += 1
    if confusions:
        print("\n  Confusion pairs (expected → predicted):")
        for (exp, pred), count in confusions.most_common(5):
            print(f"    {exp} → {pred}: {count}x")


def save_report(results: dict, cases: list[dict]) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"stress_report_{timestamp}.json"
    payload = {
        "timestamp": timestamp,
        "type": "routing_stress",
        "summary": {
            "accuracy": results["accuracy"],
            "correct": results["correct"],
            "total": results["total"],
        },
        "results": results["results"],
        "cases_meta": [{"id": c["id"], "note": c.get("note", "")} for c in cases],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run routing stress-test suite")
    parser.add_argument("--filter", metavar="INTENT", help="Only test cases for one intent")
    parser.add_argument("--save", action="store_true", help="Save JSON report to reports/")
    args = parser.parse_args()

    cases = load_stress_cases(intent_filter=args.filter)
    print(f"  Loaded {len(cases)} stress cases" + (f" (filter: {args.filter})" if args.filter else ""))

    results = run_stress_eval(cases)
    print_results(results, cases)

    if args.save:
        path = save_report(results, cases)
        print(f"\n  Report → {path}")
