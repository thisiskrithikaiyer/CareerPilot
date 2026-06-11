"""
Rewrites the <!-- EVAL_METRICS_START/END --> block in README.md with the latest eval scores.

Usage (from backend/):
    python3 -m careerpilot.eval.runners.update_readme
"""
import json
import re
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"
README = Path(__file__).parent.parent.parent.parent.parent / "README.md"

_START = "<!-- EVAL_METRICS_START -->"
_END = "<!-- EVAL_METRICS_END -->"


def _latest_report() -> dict | None:
    paths = sorted(REPORTS_DIR.glob("eval_report_*.json"))
    if not paths:
        return None
    return json.loads(paths[-1].read_text()), paths[-1].stem


def _fmt_pct(v: float | None) -> str:
    return f"**{v:.0%}**" if v is not None else "n/a"


def _fmt_score(v: float | None) -> str:
    return f"**{v:.1f}/10**" if v is not None else "n/a"


def _build_table(report: dict, ts: str) -> str:
    dt = datetime.strptime(ts.replace("eval_report_", ""), "%Y%m%d_%H%M%S")
    run_time = dt.strftime("%b %d %Y, %H:%M")

    routing = report.get("routing", {})
    intake = report.get("agent_intake", {})
    checkin = report.get("agent_checkin", {})
    acct = report.get("agent_accountability", {})
    judge = report.get("llm_judge", {})
    consist = report.get("consistency", {})

    rows = []
    hard_labels = [
        ("hard_progress_extraction", "Check-in extraction (hard)"),
        ("hard_task_close", "Task close matching (hard)"),
        ("hard_next_day_plan", "Next-day plan carryover (hard)"),
    ]
    for key, label in hard_labels:
        h = report.get(key)
        if h:
            rows.append((label, f"{_fmt_pct(h.get('pass_rate'))} ({h.get('passed', '?')}/{h.get('total', '?')})"))

    rows += [
        ("Routing accuracy", f"{_fmt_pct(routing.get('accuracy'))} ({routing.get('correct', '?')}/{routing.get('total', '?')})"),
        ("Intake agent pass rate", f"{_fmt_pct(intake.get('pass_rate'))} ({intake.get('passed', '?')}/{intake.get('total', '?')})"),
        ("Check-in agent pass rate", f"{_fmt_pct(checkin.get('pass_rate'))} ({checkin.get('passed', '?')}/{checkin.get('total', '?')})"),
        ("Accountability agent pass rate", f"{_fmt_pct(acct.get('pass_rate'))} ({acct.get('passed', '?')}/{acct.get('total', '?')})"),
    ]

    if judge:
        avg_scores = judge.get("avg_scores", {})
        rows += [
            ("LLM judge pass rate", f"{_fmt_pct(judge.get('pass_rate'))}"),
            ("  — helpfulness", f"{_fmt_score(avg_scores.get('helpfulness'))}"),
            ("  — emotional appropriateness", f"{_fmt_score(avg_scores.get('emotional_appropriateness'))}"),
            ("  — actionability", f"{_fmt_score(avg_scores.get('actionability'))}"),
            ("  — safety", f"{_fmt_score(avg_scores.get('safety'))}"),
            ("  — tone consistency", f"{_fmt_score(avg_scores.get('tone_consistency'))}"),
        ]

    if consist:
        rows += [
            ("Consistency score (avg)", f"**{consist.get('avg_consistency', 0):.3f}** / 1.0"),
            ("Consistency pass rate", f"{_fmt_pct(consist.get('pass_rate'))}"),
        ]

    table_lines = [
        f"| Eval | Score |",
        f"|------|-------|",
    ]
    for label, value in rows:
        table_lines.append(f"| {label} | {value} |")

    table_lines.append(f"\n_Last updated: {run_time}_")
    return "\n".join(table_lines)


def update_readme() -> None:
    result = _latest_report()
    if result is None:
        print("No eval reports found. Run evals first:")
        print("  python3 -m careerpilot.eval.runners.run_evals --skip-consistency")
        return

    report, stem = result
    table = _build_table(report, stem)

    readme_text = README.read_text()
    pattern = re.compile(
        rf"{re.escape(_START)}.*?{re.escape(_END)}",
        re.DOTALL,
    )

    if not pattern.search(readme_text):
        print(f"Sentinel comments not found in {README}")
        print(f"Add  {_START}  and  {_END}  around the metrics table in README.md")
        return

    new_block = f"{_START}\n{table}\n{_END}"
    updated = pattern.sub(new_block, readme_text)
    README.write_text(updated)
    print(f"README updated from report: {stem}")
    print(f"  → {README}")


if __name__ == "__main__":
    update_readme()
