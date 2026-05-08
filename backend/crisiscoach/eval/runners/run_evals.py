"""Run all evaluations: routing accuracy + end-to-end agent response quality."""
import asyncio
import json
from datetime import datetime
from pathlib import Path

DATASETS_DIR = Path(__file__).parent.parent / "datasets"
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def load_dataset(name: str) -> list[dict]:
    path = DATASETS_DIR / f"{name}_golden.json"
    with open(path) as f:
        return json.load(f)


# ── Routing accuracy ──────────────────────────────────────────────────────────

def run_routing_eval() -> dict:
    from crisiscoach.eval.evaluators.routing_accuracy import score_routing
    cases = (
        load_dataset("intake")
        + load_dataset("accountability")
        + load_dataset("checkin")
    )
    routing_cases = [
        {
            "id": c.get("id"),
            "input": c["input"],
            "expected_intent": c["expected_intent"],
            "phase": c.get("phase", "active"),
        }
        for c in cases
        if isinstance(c.get("input"), str) and c.get("expected_intent")
    ]
    return score_routing(routing_cases)


# ── Agent response quality ────────────────────────────────────────────────────

async def run_agent_eval(dataset_name: str) -> dict:
    from crisiscoach.eval.evaluators.agent_response import run_dataset
    cases = load_dataset(dataset_name)
    return await run_dataset(cases)


# ── Report helpers ────────────────────────────────────────────────────────────

def _print_routing(results: dict) -> None:
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  ROUTING ACCURACY                                    ║")
    print("╚══════════════════════════════════════════════════════╝")
    acc = results["accuracy"]
    bar = "█" * int(acc * 20) + "░" * (20 - int(acc * 20))
    print(f"  {bar}  {acc:.1%}  ({results['correct']}/{results['total']})\n")
    for r in results["results"]:
        mark = "✓" if r["correct"] else "✗"
        print(f"  {mark} [{r['id']}] expected={r['expected']} got={r['predicted']}")
        if not r["correct"]:
            print(f"      reason: {r.get('reason', '')}")


def _print_agent(name: str, results: dict) -> None:
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  AGENT RESPONSE: {name.upper():<36}║")
    print(f"╚══════════════════════════════════════════════════════╝")
    pr = results["pass_rate"]
    bar = "█" * int(pr * 20) + "░" * (20 - int(pr * 20))
    print(f"  {bar}  {pr:.1%}  ({results['passed']}/{results['total']})")
    print(f"  avg similarity: {results['avg_similarity']}\n")

    for r in results["results"]:
        mark = "✓" if r["passed"] else "✗"
        print(f"  {mark} [{r['id']}]  routed→{r['intent_routed']}  sim={r['similarity']['avg_similarity']}")
        if r.get("error"):
            print(f"      ERROR: {r['error']}")
        elif not r["passed"]:
            for kw in r["similarity"]["keyword_scores"]:
                if not kw["passed"]:
                    sim = kw.get("similarity", "?")
                    print(f"      FAIL [{kw['type']}] '{kw['phrase']}' sim={sim}")
        if r["response_snippet"]:
            print(f"      » {r['response_snippet'][:120]}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_all() -> dict:
    results: dict = {}

    print("\n🔍 Running routing eval…")
    results["routing"] = run_routing_eval()

    print("🤖 Running end-to-end agent evals…")
    for dataset in ["intake", "accountability", "checkin"]:
        print(f"   • {dataset}…")
        results[f"agent_{dataset}"] = await run_agent_eval(dataset)

    _print_routing(results["routing"])
    for dataset in ["intake", "accountability", "checkin"]:
        _print_agent(dataset, results[f"agent_{dataset}"])

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  SUMMARY                                             ║")
    print("╠════════════════════════╦═══════════╦════════════════╣")
    print("║  Eval                  ║ Pass rate ║ Avg similarity ║")
    print("╠════════════════════════╬═══════════╬════════════════╣")
    r = results["routing"]
    print(f"║  {'routing':<22} ║  {r['accuracy']:.1%}    ║  {'n/a':<12}  ║")
    for ds in ["intake", "accountability", "checkin"]:
        ar = results[f"agent_{ds}"]
        print(f"║  {'agent_' + ds:<22} ║  {ar['pass_rate']:.1%}    ║  {ar['avg_similarity']:<12}  ║")
    print("╚════════════════════════╩═══════════╩════════════════╝")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"eval_report_{timestamp}.json"
    REPORTS_DIR.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Report → {report_path}\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_all())
