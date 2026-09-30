"""Collects the results of the golden cases and writes the evaluation report (JSON and Markdown)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tests.evaluation.cases import CASES, CRITERIA
from tests.evaluation.harness import Check

RESULTS: list[Check] = []

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "reports"


def report_dir() -> Path:
    return Path(os.environ.get("EVAL_REPORT_DIR", DEFAULT_DIR))


def _cell(checks: list[Check]) -> str:
    if not checks:
        return "-"
    return "PASS" if all(c.passed for c in checks) else "FAIL"


def build_markdown(results: list[Check], generated: str) -> str:
    titles = {c.id: c.title for c in CASES}
    order = [c.id for c in CASES if any(r.case_id == c.id for r in results)]
    passed = sum(1 for r in results if r.passed)

    lines = [
        "# Gym agent evaluation report",
        "",
        f"Generated {generated}. Golden cases run through the real graph, runner, store and validator with a scripted model "
        "and fake tools; every check is a deterministic assertion on stored data (no LLM judge).",
        "",
        f"**{passed} of {len(results)} checks passed across {len(order)} golden cases.**",
        "",
        "## Criteria coverage (case x criterion)",
        "",
        "| Case | " + " | ".join(c.replace("_", " ") for c in CRITERIA) + " |",
        "|---|" + "|".join("---" for _ in CRITERIA) + "|",
    ]
    for case_id in order:
        mine = [r for r in results if r.case_id == case_id]
        lines.append(f"| {case_id} | " + " | ".join(_cell([r for r in mine if r.criterion == c]) for c in CRITERIA) + " |")
    lines.append("| **all cases** | " + " | ".join(f"**{_cell([r for r in results if r.criterion == c])}**" for c in CRITERIA) + " |")

    lines += ["", "PASS = evidenced and passed, FAIL = a check failed, - = not evidenced by this case.", "", "## Cases"]
    for case_id in order:
        lines += ["", f"### {case_id}", "", titles[case_id], "", "| Criterion | Check | Expected | Observed | Result |", "|---|---|---|---|---|"]
        for r in (r for r in results if r.case_id == case_id):
            expected = json.dumps(r.expected, default=str)
            observed = json.dumps(r.observed, default=str)
            lines.append(f"| {r.criterion.replace('_', ' ')} | {r.name} | `{expected[:70]}` | `{observed[:70]}` | {'PASS' if r.passed else 'FAIL'} |")
    return "\n".join(lines) + "\n"


def write_reports(results: list[Check] | None = None) -> Path | None:
    results = RESULTS if results is None else results
    if not results:
        return None
    out = report_dir()
    out.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (out / "evaluation_report.json").write_text(
        json.dumps(
            {
                "generated": generated,
                "cases": len({r.case_id for r in results}),
                "checks": len(results),
                "passed": sum(1 for r in results if r.passed),
                "results": [r.__dict__ for r in results],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (out / "evaluation_report.md").write_text(build_markdown(results, generated), encoding="utf-8")
    return out
