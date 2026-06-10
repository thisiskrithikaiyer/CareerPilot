"""
Eval regression dashboard — compares eval reports over time and shows score trends.

Usage:
    python -m careerpilot.eval.runners.regression_dashboard          # CLI summary
    python -m careerpilot.eval.runners.regression_dashboard --html   # + HTML file
    python -m careerpilot.eval.runners.regression_dashboard --last 5 # compare last N runs
"""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"

_METRICS = [
    ("routing", "accuracy"),
    ("agent_intake", "pass_rate"),
    ("agent_accountability", "pass_rate"),
    ("agent_checkin", "pass_rate"),
    ("llm_judge", "pass_rate"),
    ("consistency", "avg_consistency"),
]

_METRIC_LABELS = {
    ("routing", "accuracy"): "Routing accuracy",
    ("agent_intake", "pass_rate"): "Agent: intake",
    ("agent_accountability", "pass_rate"): "Agent: accountability",
    ("agent_checkin", "pass_rate"): "Agent: checkin",
    ("llm_judge", "pass_rate"): "LLM judge",
    ("consistency", "avg_consistency"): "Consistency",
}


def _load_reports(last_n: int | None = None) -> list[dict]:
    paths = sorted(REPORTS_DIR.glob("eval_report_*.json"))
    if last_n:
        paths = paths[-last_n:]
    reports = []
    for p in paths:
        try:
            data = json.loads(p.read_text())
            ts_str = p.stem.replace("eval_report_", "")
            data["_timestamp"] = ts_str
            data["_path"] = str(p)
            reports.append(data)
        except Exception:
            pass
    return reports


def _get_commit_for_timestamp(ts_str: str) -> str:
    """Best-effort: find the git commit closest to (at or before) the report timestamp."""
    try:
        dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
        result = subprocess.run(
            ["git", "log", "--oneline", "--before", iso, "-1"],
            capture_output=True, text=True, cwd=REPORTS_DIR.parent.parent.parent,
        )
        line = result.stdout.strip()
        return line[:50] if line else "unknown"
    except Exception:
        return "unknown"


def _extract_metric(report: dict, section: str, key: str) -> float | None:
    section_data = report.get(section)
    if not section_data:
        return None
    return section_data.get(key)


def _delta_str(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return "  n/a"
    d = current - previous
    if abs(d) < 0.001:
        return "  ─"
    sign = "▲" if d > 0 else "▼"
    return f" {sign}{abs(d):.1%}"


def _bar(value: float | None, width: int = 14) -> str:
    if value is None:
        return "─" * width
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def print_dashboard(reports: list[dict]) -> None:
    if not reports:
        print("No eval reports found in", REPORTS_DIR)
        return

    print("\n╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  EVAL REGRESSION DASHBOARD                                              ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")

    # Header row: timestamps
    header = f"  {'Metric':<24}"
    for r in reports[-5:]:
        ts = r["_timestamp"]
        header += f"  {ts[4:13]:<13}"
    print(header)
    print("  " + "─" * (24 + len(reports[-5:]) * 15))

    for section, key in _METRICS:
        label = _METRIC_LABELS.get((section, key), f"{section}.{key}")
        row = f"  {label:<24}"
        vals = [_extract_metric(r, section, key) for r in reports[-5:]]
        for i, v in enumerate(vals):
            prev = vals[i - 1] if i > 0 else None
            val_str = f"{v:.1%}" if v is not None else "n/a"
            delta = _delta_str(v, prev) if i > 0 else "      "
            row += f"  {val_str:<6}{delta:<7}"
        print(row)

    print("╚══════════════════════════════════════════════════════════════════════════╝")

    # Latest report summary with bar chart
    latest = reports[-1]
    print(f"\n  Latest: {latest['_timestamp']}")
    for section, key in _METRICS:
        label = _METRIC_LABELS.get((section, key), f"{section}.{key}")
        v = _extract_metric(latest, section, key)
        bar = _bar(v)
        val_str = f"{v:.1%}" if v is not None else "n/a"
        print(f"  {label:<26} {bar}  {val_str}")

    # Biggest regressions
    if len(reports) >= 2:
        prev, curr = reports[-2], reports[-1]
        drops = []
        for section, key in _METRICS:
            p = _extract_metric(prev, section, key)
            c = _extract_metric(curr, section, key)
            if p is not None and c is not None and c < p - 0.02:
                label = _METRIC_LABELS.get((section, key), f"{section}.{key}")
                drops.append((label, p, c, c - p))
        if drops:
            print("\n  ⚠ Regressions since last run:")
            for label, p, c, d in sorted(drops, key=lambda x: x[3]):
                print(f"    {label:<26} {p:.1%} → {c:.1%}  ({d:+.1%})")
        else:
            print("\n  ✓ No regressions since last run")


def _format_cell(v: float | None, prev: float | None) -> str:
    if v is None:
        return "<td class='na'>—</td>"
    val_str = f"{v:.1%}"
    if prev is None:
        return f"<td>{val_str}</td>"
    d = v - prev
    if d > 0.02:
        return f"<td class='up'>{val_str} ▲{d:.1%}</td>"
    if d < -0.02:
        return f"<td class='down'>{val_str} ▼{abs(d):.1%}</td>"
    return f"<td>{val_str}</td>"


def generate_html(reports: list[dict]) -> str:
    rows_html = ""
    for i, r in enumerate(reports):
        ts = r["_timestamp"]
        dt = datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%b %d %H:%M")
        commit = _get_commit_for_timestamp(ts)
        cells = f"<td>{dt}</td><td class='commit'>{commit}</td>"
        for section, key in _METRICS:
            v = _extract_metric(r, section, key)
            prev_v = _extract_metric(reports[i - 1], section, key) if i > 0 else None
            cells += _format_cell(v, prev_v)
        rows_html += f"<tr>{cells}</tr>\n"

    headers = "".join(
        f"<th>{_METRIC_LABELS.get((s, k), f'{s}.{k}')}</th>"
        for s, k in _METRICS
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CrisisCoach Eval Regression Dashboard</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0d1117; color: #e6edf3; margin: 0; padding: 24px; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; color: #58a6ff; }}
  p.sub {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 24px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
  th {{ background: #161b22; color: #8b949e; padding: 8px 12px;
        text-align: left; border-bottom: 1px solid #30363d; white-space: nowrap; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #21262d; white-space: nowrap; }}
  tr:hover td {{ background: #161b22; }}
  td.up {{ color: #3fb950; font-weight: 600; }}
  td.down {{ color: #f85149; font-weight: 600; }}
  td.na {{ color: #484f58; }}
  td.commit {{ font-family: monospace; font-size: 0.78rem; color: #8b949e;
               max-width: 220px; overflow: hidden; text-overflow: ellipsis; }}
  .generated {{ color: #484f58; font-size: 0.75rem; margin-top: 16px; }}
</style>
</head>
<body>
<h1>CrisisCoach — Eval Regression Dashboard</h1>
<p class="sub">Tracking {len(reports)} eval run(s). Green = improvement ≥2pp, Red = regression ≥2pp.</p>
<table>
  <thead><tr><th>Run</th><th>Commit</th>{headers}</tr></thead>
  <tbody>{rows_html}</tbody>
</table>
<p class="generated">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</body>
</html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval regression dashboard")
    parser.add_argument("--last", type=int, default=None, help="Show last N reports")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    args = parser.parse_args()

    reports = _load_reports(last_n=args.last)
    print_dashboard(reports)

    if args.html:
        html = generate_html(reports)
        out = REPORTS_DIR / "dashboard.html"
        out.write_text(html)
        print(f"\n  HTML → {out}")
