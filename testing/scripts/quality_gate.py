#!/usr/bin/env python3
"""BankTest CI quality gate.

Reads testing/reports/results.json and exits 1 when:
  * results.json is missing/unreadable or no tests were executed,
  * any Critical test failed or errored,
  * the pass rate is below MIN_PASS_RATE (env, percent; default 0 = disabled),
  * PYTEST_EXIT_CODE (env, optional) shows pytest crashed rather than ran
    (anything other than 0 = all passed, 1 = some tests failed).

Prints a summary and appends a Markdown version to $GITHUB_STEP_SUMMARY when set.

Usage: python scripts/quality_gate.py [path/to/results.json]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_RESULTS = Path(__file__).resolve().parent.parent / "reports" / "results.json"
ICON = {"passed": "PASS", "failed": "FAIL", "error": "ERROR", "skipped": "SKIP"}


def write_step_summary(markdown: str) -> None:
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(markdown + "\n")


def fail_early(reason: str) -> int:
    print(f"QUALITY GATE: FAILED — {reason}")
    write_step_summary(f"## BankTest quality gate: FAILED\n\n{reason}\n")
    return 1


def main(argv: list[str]) -> int:
    results_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_RESULTS
    try:
        min_pass_rate = float(os.getenv("MIN_PASS_RATE", "0") or 0)
    except ValueError:
        return fail_early(f"MIN_PASS_RATE={os.getenv('MIN_PASS_RATE')!r} is not a number.")

    if not results_path.exists():
        return fail_early(f"{results_path} was not produced — the test run did not complete.")
    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
        summary, tests, run = data["summary"], data["tests"], data["run"]
    except (OSError, ValueError, KeyError) as exc:
        return fail_early(f"{results_path} is unreadable: {exc}")

    critical_failures = [
        t for t in tests if t.get("priority") == "Critical" and t.get("outcome") in ("failed", "error")
    ]
    other_failures = [
        t for t in tests if t.get("outcome") in ("failed", "error") and t not in critical_failures
    ]
    pass_rate = float(summary.get("pass_rate", 0))

    reasons = []
    if summary.get("total", 0) == 0:
        reasons.append("No tests were executed.")
    if critical_failures:
        reasons.append(f"{len(critical_failures)} Critical test(s) failed.")
    if min_pass_rate > 0 and pass_rate < min_pass_rate:
        reasons.append(f"Pass rate {pass_rate:.2f}% is below the required {min_pass_rate:.2f}%.")
    exit_code = os.getenv("PYTEST_EXIT_CODE", "").strip()
    if exit_code and exit_code not in ("0", "1"):
        reasons.append(f"pytest exited with code {exit_code} (interrupted, internal or usage error).")

    status = "FAILED" if reasons else "PASSED"
    gate_rule = f"pass rate >= {min_pass_rate:.2f}%" if min_pass_rate > 0 else "pass-rate threshold disabled"

    # ── console ──────────────────────────────────────────────────────────────
    print("=" * 72)
    print(f"BankTest quality gate: {status}")
    print(f"Commit {run.get('commit_sha') or 'unknown'} on {run.get('branch') or 'unknown'} "
          f"({run.get('trigger')}), base URL {run.get('base_url')}")
    print(f"Total {summary.get('total')} | passed {summary.get('passed')} | failed {summary.get('failed')} | "
          f"error {summary.get('error')} | skipped {summary.get('skipped')} | pass rate {pass_rate:.2f}% "
          f"| critical failed {len(critical_failures)} | {gate_rule}")
    for t in critical_failures + other_failures:
        print(f"  [{ICON.get(t['outcome'], t['outcome'])}] {t['tc_id']} ({t['priority']}) {t['title']}: "
              f"{(t.get('message') or '').splitlines()[0] if t.get('message') else ''}")
    for reason in reasons:
        print(f"  -> {reason}")
    print("=" * 72)

    # ── GitHub step summary ──────────────────────────────────────────────────
    md = [
        f"## BankTest quality gate: {status}",
        "",
        "| Total | Passed | Failed | Error | Skipped | Pass rate | Critical failed |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {summary.get('total')} | {summary.get('passed')} | {summary.get('failed')} | {summary.get('error')} "
        f"| {summary.get('skipped')} | {pass_rate:.2f}% | {len(critical_failures)} |",
        "",
        f"Commit `{run.get('commit_sha') or 'unknown'}` · branch `{run.get('branch') or 'unknown'}` · "
        f"trigger `{run.get('trigger')}` · browser `{run.get('browser')}` · {gate_rule}",
    ]
    if reasons:
        md += ["", "**Gate failed because:**", *[f"- {r}" for r in reasons]]
    if critical_failures or other_failures:
        md += ["", "| Result | TC ID | Priority | Title | Message |", "|---|---|---|---|---|"]
        for t in critical_failures + other_failures:
            message = (t.get("message") or "").splitlines()[0].replace("|", "\\|")[:200] if t.get("message") else ""
            md.append(f"| {ICON.get(t['outcome'])} | {t['tc_id']} | {t['priority']} | {t['title']} | {message} |")
    md += ["", "Full evidence (JUnit, HTML report, screenshots, server log) is in the `test-results` artifact."]
    write_step_summary("\n".join(md))

    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
