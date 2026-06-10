"""Run all evaluations: routing accuracy + end-to-end agent quality + LLM judge + consistency."""
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
    from careerpilot.eval.evaluators.routing_accuracy import score_routing
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
    from careerpilot.eval.evaluators.agent_response import run_dataset
    cases = load_dataset(dataset_name)
    return await run_dataset(cases)


# ── LLM-as-Judge ─────────────────────────────────────────────────────────────

async def run_llm_judge(dataset_name: str, agent_results: dict) -> dict:
    """Score the agent responses from a completed agent eval using the LLM judge."""
    from careerpilot.eval.evaluators.llm_judge import judge_dataset
    cases = load_dataset(dataset_name)
    run_results = agent_results.get("results", [])
    return judge_dataset(cases, run_results)


# ── Consistency ───────────────────────────────────────────────────────────────

async def run_consistency_eval(dataset_name: str, n_runs: int = 5) -> dict:
    from careerpilot.eval.evaluators.consistency import run_consistency_suite
    cases = load_dataset(dataset_name)
    return await run_consistency_suite(cases, n_runs=n_runs)


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


def _print_llm_judge(name: str, results: dict) -> None:
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  LLM JUDGE: {name.upper():<42}║")
    print(f"╚══════════════════════════════════════════════════════╝")
    pr = results["pass_rate"]
    bar = "█" * int(pr * 20) + "░" * (20 - int(pr * 20))
    print(f"  {bar}  {pr:.1%} pass rate")
    avg = results.get("avg_scores", {})
    for dim, score in avg.items():
        if dim != "computed_avg":
            dim_bar = "█" * int((score / 10) * 12) + "░" * (12 - int((score / 10) * 12))
            print(f"  {dim:<28} {dim_bar}  {score:.1f}/10")


def _print_consistency(name: str, results: dict) -> None:
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  CONSISTENCY: {name.upper():<39}║")
    print(f"╚══════════════════════════════════════════════════════╝")
    avg = results.get("avg_consistency", 0)
    pr = results.get("pass_rate", 0)
    bar = "█" * int(avg * 20) + "░" * (20 - int(avg * 20))
    print(f"  {bar}  {avg:.3f} avg score  ({results['total_cases']} cases × {results['n_runs_per_case']} runs)")
    print(f"  pass rate: {pr:.1%}\n")
    for r in results.get("results", []):
        mark = "✓" if r.get("passed") else "✗"
        print(
            f"  {mark} [{r['id']}]  "
            f"routing={r.get('routing_agreement', 0):.0%}  "
            f"length_cv={r.get('length_cv', 0):.2f}  "
            f"score={r.get('consistency_score', 0):.3f}"
        )


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_all(skip_consistency: bool = False, consistency_runs: int = 5) -> dict:
    results: dict = {}

    print("\n🔍 Running routing eval…")
    results["routing"] = run_routing_eval()

    print("🤖 Running end-to-end agent evals…")
    for dataset in ["intake", "accountability", "checkin"]:
        print(f"   • {dataset}…")
        results[f"agent_{dataset}"] = await run_agent_eval(dataset)

    print("⚖️  Running LLM-as-Judge on intake responses…")
    results["llm_judge"] = await run_llm_judge("intake", results["agent_intake"])

    if not skip_consistency:
        print(f"🔁 Running consistency eval (intake × {consistency_runs} runs)…")
        results["consistency"] = await run_consistency_eval("intake", n_runs=consistency_runs)

    # ── Print all results ────────────────────────────────────────────────────
    _print_routing(results["routing"])
    for dataset in ["intake", "accountability", "checkin"]:
        _print_agent(dataset, results[f"agent_{dataset}"])
    _print_llm_judge("intake", results["llm_judge"])
    if not skip_consistency:
        _print_consistency("intake", results["consistency"])

    # ── Summary table ────────────────────────────────────────────────────────
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  SUMMARY                                             ║")
    print("╠══════════════════════╦════════════╦═════════════════╣")
    print("║  Eval                ║ Pass rate  ║ Avg / score     ║")
    print("╠══════════════════════╬════════════╬═════════════════╣")

    r = results["routing"]
    print(f"║  {'routing':<20} ║  {r['accuracy']:.1%}     ║  {'n/a':<13}  ║")
    for ds in ["intake", "accountability", "checkin"]:
        ar = results[f"agent_{ds}"]
        print(f"║  {'agent_' + ds:<20} ║  {ar['pass_rate']:.1%}     ║  sim {ar['avg_similarity']:<8}  ║")
    jr = results["llm_judge"]
    avg_judge = jr.get("avg_scores", {}).get("computed_avg", 0)
    print(f"║  {'llm_judge':<20} ║  {jr['pass_rate']:.1%}     ║  {avg_judge:.1f}/10{'':<9}  ║")
    if not skip_consistency:
        cr = results["consistency"]
        print(f"║  {'consistency':<20} ║  {cr['pass_rate']:.1%}     ║  {cr['avg_consistency']:.3f}{'':<9}  ║")

    print("╚══════════════════════╩════════════╩═════════════════╝")

    # ── Save report ──────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"eval_report_{timestamp}.json"
    REPORTS_DIR.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Report → {report_path}\n")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run CrisisCoach evals")
    parser.add_argument("--skip-consistency", action="store_true",
                        help="Skip the multi-run consistency eval (faster)")
    parser.add_argument("--consistency-runs", type=int, default=5,
                        help="Number of runs per case for consistency eval")
    args = parser.parse_args()
    asyncio.run(run_all(
        skip_consistency=args.skip_consistency,
        consistency_runs=args.consistency_runs,
    ))
