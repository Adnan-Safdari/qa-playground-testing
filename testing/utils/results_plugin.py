"""BankTest results plugin.

- Every test must carry `@pytest.mark.testcase("SB-XX-NN")` naming an entry of
  `testing/test_cases.json`; title/module/priority are joined from that catalogue.
- On a failure (setup or call) a full-page screenshot is written to
  `reports/screenshots/<tc_id>_<UTC timestamp>.png` and embedded in report.html.
- At the end of the session `reports/results.json` is written exactly per
  APP_CONTRACT.md §4 — the Streamlit dashboard parses it.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from utils.screenshots import save_screenshot

PLUGIN_NAME = "banktest-results"
SCHEMA_VERSION = 1
TC_KEY = pytest.StashKey[dict]()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def compact(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _git(repo_dir: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo_dir, capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def run_metadata(repo_dir: Path) -> dict:
    """Git / GitHub Actions context for the run (null where unknown)."""
    env = os.environ
    gh_run_id = env.get("GITHUB_RUN_ID")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "1")
    repo = env.get("GITHUB_REPOSITORY")
    server = env.get("GITHUB_SERVER_URL", "https://github.com")

    branch = env.get("GITHUB_HEAD_REF") or env.get("GITHUB_REF_NAME") or _git(
        repo_dir, "rev-parse", "--abbrev-ref", "HEAD"
    )
    if branch == "HEAD":  # detached HEAD
        branch = None

    if gh_run_id:
        run_id = gh_run_id if attempt in ("", "1") else f"{gh_run_id}-attempt-{attempt}"
    else:
        run_id = None  # filled with local-<start timestamp> by the plugin

    return {
        "run_id": run_id,
        # COMMIT_SHA lets CI report the PR head commit instead of the synthetic merge commit.
        "commit_sha": env.get("COMMIT_SHA") or env.get("GITHUB_SHA") or _git(repo_dir, "rev-parse", "HEAD"),
        "branch": branch,
        "workflow_run_id": gh_run_id or None,
        "workflow_run_url": f"{server}/{repo}/actions/runs/{gh_run_id}" if gh_run_id and repo else None,
        "trigger": env.get("GITHUB_EVENT_NAME") or "local",
    }


def load_catalogue(path: Path) -> dict[str, dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    return {case["tc_id"]: case for case in cases}


def _short_message(report) -> str | None:
    longrepr = report.longrepr
    if longrepr is None:
        return None
    if isinstance(longrepr, tuple) and len(longrepr) == 3:  # skip: (path, lineno, reason)
        return str(longrepr[2])
    crash = getattr(longrepr, "reprcrash", None)
    message = crash.message if crash is not None else str(longrepr).strip().splitlines()[-1]
    return message if len(message) <= 1000 else message[:997] + "..."


def _failure_context(driver, page_url: str) -> dict:
    """Extra evidence for the bug report: where the browser was and what the console said."""
    context = {"url": page_url, "page_title": None, "console_errors": [], "captured_at": iso(utc_now())}
    try:
        context["page_title"] = driver.title
    except Exception:
        pass
    try:
        context["console_errors"] = [
            entry.get("message", "") for entry in driver.get_log("browser") if entry.get("level") == "SEVERE"
        ][:20]
    except Exception:  # logging capability unavailable
        pass
    return context


def bug_report_markdown(test: dict, case: dict, run: dict) -> str:
    """A tracker-ready bug report for one failed test."""
    ctx = test.get("failure_context") or {}
    severity = {"Critical": "S1 - Critical", "High": "S2 - Major", "Medium": "S3 - Moderate"}.get(
        test["priority"], "S4 - Minor")
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(case.get("steps") or [], 1)) or "_See test code._"
    console = "\n".join(f"- `{m}`" for m in ctx.get("console_errors") or []) or "_None captured._"
    commit = (run.get("commit_sha") or "unknown")[:7]
    lines = [
        f"# 🐞 BUG-{test['tc_id']}: {test['title']}",
        "",
        "| Field | Value |", "|---|---|",
        f"| Test case | `{test['tc_id']}` ({test['nodeid']}) |",
        f"| Module | {test['module']} |",
        f"| Priority / Severity | {test['priority']} / {severity} |",
        f"| Status | Open |",
        f"| Detected | {ctx.get('captured_at') or run.get('finished_at')} |",
        f"| Environment | {run.get('browser') or 'chrome'}{' (headless)' if run.get('headless') else ''} · {run.get('base_url')} |",
        f"| Build | commit `{commit}` on `{run.get('branch') or 'unknown'}` · run `{run.get('run_id')}` |",
        f"| Page at failure | {ctx.get('url') or 'n/a'} — \"{ctx.get('page_title') or ''}\" |",
        "",
        "## Summary", case.get("objective") or test["title"], "",
        "## Preconditions", case.get("preconditions") or "—", "",
        "## Test data", case.get("test_data") or "—", "",
        "## Steps to reproduce", steps, "",
        "## Expected result", case.get("expected_result") or "—", "",
        "## Actual result", test.get("message") or "—", "",
        "## Evidence",
        f"![screenshot](../{test['screenshot']})" if test.get("screenshot") else "_No screenshot._", "",
        "### Browser console errors", console, "",
        "### Stack trace", "```", (test.get("traceback") or "").strip()[-6000:], "```", "",
    ]
    if run.get("workflow_run_url"):
        lines += [f"CI run: {run['workflow_run_url']}", ""]
    return "\n".join(lines)


class ResultsPlugin:
    def __init__(self, config: pytest.Config, testing_dir: Path, reports_dir: Path, catalogue_path: Path):
        self.config = config
        self.testing_dir = testing_dir
        self.reports_dir = reports_dir
        self.screenshots_dir = reports_dir / "screenshots"
        self.bug_reports_dir = reports_dir / "bug_reports"
        self.results_path = reports_dir / "results.json"
        self.catalogue = load_catalogue(catalogue_path)
        self.results: dict[str, dict] = {}
        self.started_at: datetime | None = None
        self.browser: str | None = None  # set by the driver fixture
        self.headless = env_flag("HEADLESS", True)
        self.base_url = os.getenv("BASE_URL", "http://localhost:3000").rstrip("/")
        self.meta = run_metadata(testing_dir.parent)

    # ── session ──────────────────────────────────────────────────────────────
    def pytest_sessionstart(self, session):
        self.started_at = utc_now()
        if getattr(self.config.option, "collectonly", False):
            return
        # Keep the reports folder limited to this run's evidence.
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        for old in self.screenshots_dir.glob("*.png"):
            old.unlink()
        if self.bug_reports_dir.exists():
            for old in self.bug_reports_dir.glob("*.md"):
                old.unlink()
        if self.results_path.exists():
            self.results_path.unlink()

    # tryfirst: the auto-added `critical` marker must exist before `-m` deselection runs.
    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, session, config, items):
        problems, seen = [], {}
        for item in items:
            marker = item.get_closest_marker("testcase")
            if marker is None or not marker.args:
                problems.append(f"{item.nodeid}: missing @pytest.mark.testcase('SB-XX-NN')")
                continue
            tc_id = marker.args[0]
            case = self.catalogue.get(tc_id)
            if case is None:
                problems.append(f"{item.nodeid}: {tc_id} is not in test_cases.json")
                continue
            if tc_id in seen:
                problems.append(f"{item.nodeid}: {tc_id} is already used by {seen[tc_id]}")
                continue
            seen[tc_id] = item.nodeid
            item.stash[TC_KEY] = {
                "tc_id": tc_id,
                "title": case["title"],
                "module": case["module"],
                "priority": case["priority"],
            }
            if case["priority"] == "Critical":
                item.add_marker(pytest.mark.critical)
            item.user_properties.extend(
                [("tc_id", tc_id), ("module", case["module"]), ("priority", case["priority"])]
            )
        if problems:
            raise pytest.UsageError("Test-case mapping errors:\n  " + "\n  ".join(problems))

    # ── per test ─────────────────────────────────────────────────────────────
    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_makereport(self, item, call):
        report = yield
        info = item.stash.get(TC_KEY, None) or {
            "tc_id": item.nodeid, "title": item.name, "module": "Unmapped", "priority": "Medium",
        }
        report.tc_id = info["tc_id"]
        report.priority = info["priority"]

        if report.failed and report.when in ("setup", "call"):
            self._capture_failure(item, report, info["tc_id"])
        self._record(item, report, info)
        return report

    def _capture_failure(self, item, report, tc_id: str) -> None:
        driver = getattr(item, "banktest_driver", None)
        if driver is None:
            return
        name = f"{tc_id}_{compact(utc_now())}.png"
        try:
            png = save_screenshot(driver, self.screenshots_dir / name)
            page_url = driver.current_url
        except Exception as exc:  # browser already gone, etc. — never mask the real failure
            report.sections.append(("screenshot", f"Could not capture screenshot: {exc!r}"))
            return
        report.banktest_screenshot = f"screenshots/{name}"
        report.banktest_context = _failure_context(driver, page_url)

        html = self.config.pluginmanager.getplugin("html")
        if html is not None:
            extras = getattr(report, "extras", [])
            extras.append(html.extras.png(base64.b64encode(png).decode("ascii"), name=name))
            extras.append(html.extras.url(page_url, name="Page URL at failure"))
            report.extras = extras

    def _record(self, item, report, info: dict) -> None:
        entry = self.results.get(item.nodeid)
        if entry is None:
            entry = self.results[item.nodeid] = {
                **info,
                "nodeid": item.nodeid,
                "outcome": "passed",
                "duration_seconds": 0.0,
                "message": None,
                "traceback": None,
                "screenshot": None,
                "failure_context": None,
            }
        entry["duration_seconds"] += report.duration
        screenshot = getattr(report, "banktest_screenshot", None)
        if screenshot:
            entry["screenshot"] = screenshot
        context = getattr(report, "banktest_context", None)
        if context:
            entry["failure_context"] = context

        if report.when == "setup":
            if report.skipped:
                entry.update(outcome="skipped", message=_short_message(report))
            elif report.failed:
                entry.update(outcome="error", message=_short_message(report), traceback=report.longreprtext)
        elif report.when == "call":
            if hasattr(report, "wasxfail"):
                entry["outcome"] = "skipped" if report.skipped else "passed"
                entry["message"] = f"xfail: {report.wasxfail}" if report.wasxfail else None
            elif report.failed:
                entry.update(outcome="failed", message=_short_message(report), traceback=report.longreprtext)
            elif report.skipped:
                entry.update(outcome="skipped", message=_short_message(report))
            else:
                entry["outcome"] = "passed"
        elif report.when == "teardown" and report.failed and entry["outcome"] in ("passed", "skipped"):
            entry.update(outcome="error", message=_short_message(report), traceback=report.longreprtext)

    # ── finish ───────────────────────────────────────────────────────────────
    def pytest_sessionfinish(self, session, exitstatus):
        if getattr(self.config.option, "collectonly", False):
            return
        finished = utc_now()
        started = self.started_at or finished
        tests = list(self.results.values())
        for t in tests:
            t["duration_seconds"] = round(t["duration_seconds"], 2)

        counts = {k: sum(1 for t in tests if t["outcome"] == k) for k in ("passed", "failed", "skipped", "error")}
        total = len(tests)
        executed = total - counts["skipped"]
        summary = {
            "total": total,
            **counts,
            "pass_rate": round(counts["passed"] / executed * 100, 2) if executed else 0,
            "critical_failed": sum(
                1 for t in tests if t["priority"] == "Critical" and t["outcome"] in ("failed", "error")
            ),
        }

        run = {
            "run_id": self.meta["run_id"] or f"local-{compact(started)}",
            "started_at": iso(started),
            "finished_at": iso(finished),
            "duration_seconds": round((finished - started).total_seconds(), 2),
            "commit_sha": self.meta["commit_sha"],
            "branch": self.meta["branch"],
            "workflow_run_id": self.meta["workflow_run_id"],
            "workflow_run_url": self.meta["workflow_run_url"],
            "trigger": self.meta["trigger"],
            "base_url": self.base_url,
            "browser": self.browser,
            "headless": self.headless,
        }
        ordered_keys = (
            "tc_id", "title", "module", "priority", "nodeid", "outcome",
            "duration_seconds", "message", "traceback", "screenshot", "failure_context",
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run": run,
            "summary": summary,
            "tests": [{k: t[k] for k in ordered_keys} for t in tests],
        }
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._write_bug_reports(run, tests)

    def _write_bug_reports(self, run: dict, tests: list[dict]) -> None:
        failing = [t for t in tests if t["outcome"] in ("failed", "error")]
        if not failing:
            return
        self.bug_reports_dir.mkdir(parents=True, exist_ok=True)
        for t in failing:
            md = bug_report_markdown(t, self.catalogue.get(t["tc_id"], {}), run)
            (self.bug_reports_dir / f"{t['tc_id']}.md").write_text(md, encoding="utf-8")

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        if getattr(self.config.option, "collectonly", False):
            return
        terminalreporter.write_sep("-", f"BankTest results written to {self.results_path}")

    # ── pytest-html customisation ────────────────────────────────────────────
    def pytest_html_report_title(self, report):
        report.title = "SecureBank Regression Report — BankTest"

    def pytest_html_results_table_header(self, cells):
        cells.insert(1, '<th class="sortable" data-column-type="tc_id">TC ID</th>')
        cells.insert(2, '<th class="sortable" data-column-type="priority">Priority</th>')

    def pytest_html_results_table_row(self, report, cells):
        cells.insert(1, f'<td class="col-tc_id">{getattr(report, "tc_id", "")}</td>')
        cells.insert(2, f'<td class="col-priority">{getattr(report, "priority", "")}</td>')
