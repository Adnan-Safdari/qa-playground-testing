"""Ingest BankTest pytest results into the dashboard's SQLite history.

Usage:
    python dashboard/ingest.py local [REPORTS_DIR]          # default: testing/reports
    python dashboard/ingest.py github [--limit N] [--force]  # needs GITHUB_TOKEN
    python dashboard/ingest.py prune --keep N                # retention

Input contract: testing/APP_CONTRACT.md sections 4 and 5 (results.json
schema_version 1 and testing/test_cases.json).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

from storage import HistoryStore

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = REPO_ROOT / "testing" / "reports"
DEFAULT_CATALOGUE_PATH = REPO_ROOT / "testing" / "test_cases.json"

SUPPORTED_SCHEMA_VERSIONS = {1}
OUTCOMES = ("passed", "failed", "error", "skipped")
FAILING_OUTCOMES = ("failed", "error")
_OUTCOME_ALIASES = {
    "pass": "passed", "success": "passed", "xpassed": "passed", "xpass": "passed",
    "fail": "failed", "failure": "failed",
    "errored": "error", "broken": "error",
    "skip": "skipped", "xfailed": "skipped", "xfail": "skipped",
}

DEFAULT_REPO = "Adnan-Safdari/qa-playground-testing"
WORKFLOW_FILE = "selenium-tests.yml"
ARTIFACT_NAME = "test-results"
GITHUB_API = "https://api.github.com"
MAX_ARTIFACT_BYTES = 500 * 1024 * 1024          # compressed download cap
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024        # zip-bomb guard


class IngestError(Exception):
    """The input files are missing or don't match the contract."""


# --------------------------------------------------------------------------
# Paths / config
# --------------------------------------------------------------------------
def reports_dir_from_env() -> Path:
    env = os.environ.get("BANKTEST_REPORTS_DIR")
    return Path(env).expanduser() if env else DEFAULT_REPORTS_DIR


def catalogue_path_from_env() -> Path:
    env = os.environ.get("BANKTEST_CATALOGUE_PATH")
    return Path(env).expanduser() if env else DEFAULT_CATALOGUE_PATH


def resolve_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def resolve_repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO


# --------------------------------------------------------------------------
# results.json parsing
# --------------------------------------------------------------------------
def _to_float(value) -> float | None:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _to_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _iso(value) -> str | None:
    """Normalise a timestamp to ISO-8601 UTC ('...Z'); keep unparseable text as-is."""
    ts = _parse_ts(value)
    if ts:
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return _to_str(value)


def normalise_outcome(value) -> str:
    text = (_to_str(value) or "").lower()
    text = _OUTCOME_ALIASES.get(text, text)
    # Anything outside the contract's four outcomes is kept visible as "unknown".
    return text if text in OUTCOMES else "unknown"


def pass_rate(passed: int, total: int, skipped: int) -> float:
    denominator = total - skipped
    return round(passed / denominator * 100, 2) if denominator > 0 else 0.0


def read_results_file(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise IngestError(f"results file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IngestError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise IngestError(f"{path}: expected a JSON object at the top level")
    version = data.get("schema_version")
    if version is None:
        raise IngestError(f"{path}: missing schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise IngestError(
            f"{path}: unsupported schema_version {version!r} "
            f"(supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)})"
        )
    return data


def _normalise_test(raw: dict) -> dict:
    return {
        "tc_id": _to_str(raw.get("tc_id")),
        "title": _to_str(raw.get("title")),
        "module": _to_str(raw.get("module")),
        "priority": _to_str(raw.get("priority")),
        "nodeid": _to_str(raw.get("nodeid")),
        "outcome": normalise_outcome(raw.get("outcome")),
        "duration_seconds": _to_float(raw.get("duration_seconds")),
        "message": _to_str(raw.get("message")),
        "traceback": _to_str(raw.get("traceback")),
        "screenshot": _to_str(raw.get("screenshot")),
    }


def normalise_results(data: dict, defaults: dict | None = None) -> tuple[dict, list[dict]]:
    """Turn a validated results.json dict into (run, tests) rows for storage.

    ``defaults`` fill run fields that are missing/null in the file (used to
    enrich GitHub runs with API metadata); they never override file values.
    Counts are recomputed from ``tests`` when the list is non-empty so the
    summary always agrees with the per-test rows; the file's ``summary`` is
    used only when no per-test data is present.
    """
    run_in = data.get("run") if isinstance(data.get("run"), dict) else {}
    tests_in = data.get("tests") if isinstance(data.get("tests"), list) else []
    summary_in = data.get("summary") if isinstance(data.get("summary"), dict) else {}

    tests = [_normalise_test(t) for t in tests_in if isinstance(t, dict)]

    run = {
        "run_id": _to_str(run_in.get("run_id")),
        "started_at": _iso(run_in.get("started_at")),
        "finished_at": _iso(run_in.get("finished_at")),
        "duration_seconds": _to_float(run_in.get("duration_seconds")),
        "commit_sha": _to_str(run_in.get("commit_sha")),
        "branch": _to_str(run_in.get("branch")),
        "workflow_run_id": _to_str(run_in.get("workflow_run_id")),
        "workflow_run_url": _to_str(run_in.get("workflow_run_url")),
        "trigger": _to_str(run_in.get("trigger")),
        "base_url": _to_str(run_in.get("base_url")),
        "browser": _to_str(run_in.get("browser")),
        "headless": run_in.get("headless") if isinstance(run_in.get("headless"), bool) else None,
        "schema_version": data.get("schema_version"),
    }
    for key, value in (defaults or {}).items():
        if run.get(key) is None and value is not None:
            run[key] = _iso(value) if key in ("started_at", "finished_at") else value

    if not run["run_id"]:
        run["run_id"] = run["workflow_run_id"]
    if not run["run_id"] and run["started_at"]:
        stamp = run["started_at"].replace("-", "").replace(":", "")
        run["run_id"] = f"local-{stamp}"
    if not run["run_id"]:
        raise IngestError("results.json has no run.run_id, workflow_run_id or started_at to identify the run")

    if run["duration_seconds"] is None:
        start, end = _parse_ts(run["started_at"]), _parse_ts(run["finished_at"])
        if start and end:
            run["duration_seconds"] = round((end - start).total_seconds(), 2)
        elif tests:
            run["duration_seconds"] = round(sum(t["duration_seconds"] or 0 for t in tests), 2)

    if tests:
        counts = {o: sum(1 for t in tests if t["outcome"] == o) for o in OUTCOMES}
        total = len(tests)
        critical = sum(
            1 for t in tests
            if t["outcome"] in FAILING_OUTCOMES and (t["priority"] or "").lower() == "critical"
        )
    else:
        def _int(key):
            try:
                return int(summary_in.get(key) or 0)
            except (TypeError, ValueError):
                return 0
        counts = {o: _int(o) for o in OUTCOMES}
        total = _int("total") or sum(counts.values())
        critical = _int("critical_failed")

    run.update(counts)
    run["total"] = total
    run["critical_failed"] = critical
    run["pass_rate"] = pass_rate(counts["passed"], total, counts["skipped"])
    return run, tests


# --------------------------------------------------------------------------
# Catalogue (testing/test_cases.json)
# --------------------------------------------------------------------------
def load_catalogue(path: Path | None = None) -> tuple[list[dict], str | None]:
    """Return (cases, error). Missing file -> ([], None); invalid -> ([], message)."""
    path = Path(path) if path else catalogue_path_from_env()
    if not path.is_file():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [], f"{path.name} is not valid JSON: {exc}"
    if not isinstance(data, list):
        return [], f"{path.name}: expected a JSON array of test cases"
    cases = []
    for raw in data:
        if not isinstance(raw, dict) or not _to_str(raw.get("tc_id")):
            continue
        steps = raw.get("steps")
        if isinstance(steps, str):
            steps = [steps]
        elif not isinstance(steps, list):
            steps = []
        cases.append({
            "tc_id": _to_str(raw.get("tc_id")),
            "module": _to_str(raw.get("module")) or "Unassigned",
            "title": _to_str(raw.get("title")) or "",
            "objective": _to_str(raw.get("objective")),
            "preconditions": _to_str(raw.get("preconditions")),
            "test_data": _to_str(raw.get("test_data")),
            "steps": [str(s) for s in steps],
            "expected_result": _to_str(raw.get("expected_result")),
            "priority": _to_str(raw.get("priority")) or "Unspecified",
            "automated": bool(raw.get("automated")),
            "status": _to_str(raw.get("status")) or "Unspecified",
            "notes": _to_str(raw.get("notes")),
        })
    return cases, None


# --------------------------------------------------------------------------
# Local ingest
# --------------------------------------------------------------------------
@dataclass
class IngestResult:
    run_id: str
    replaced: bool
    total: int
    passed: int
    failed: int
    error: int
    skipped: int

    def describe(self) -> str:
        verb = "re-ingested" if self.replaced else "ingested"
        return (f"{verb} run {self.run_id}: {self.total} tests — {self.passed} passed, "
                f"{self.failed} failed, {self.error} error, {self.skipped} skipped")


def find_results_file(root: Path) -> Path | None:
    root = Path(root)
    direct = root / "results.json"
    if direct.is_file():
        return direct
    candidates = sorted(root.rglob("results.json"), key=lambda p: len(p.parts))
    return candidates[0] if candidates else None


def ingest_reports_dir(store: HistoryStore, reports_dir: Path | None = None, source: str = "local",
                       defaults: dict | None = None) -> IngestResult:
    reports_dir = Path(reports_dir) if reports_dir else reports_dir_from_env()
    if not reports_dir.is_dir():
        raise IngestError(f"reports directory not found: {reports_dir}")
    results_path = find_results_file(reports_dir)
    if results_path is None:
        raise IngestError(f"no results.json in {reports_dir}")
    run, tests = normalise_results(read_results_file(results_path), defaults)
    tests = store.store_artifacts(run["run_id"], results_path.parent, tests)
    replaced = store.save_run(run, tests, source=source)
    return IngestResult(run["run_id"], replaced, run["total"], run["passed"],
                        run["failed"], run["error"], run["skipped"])


# --------------------------------------------------------------------------
# GitHub Actions ingest
# --------------------------------------------------------------------------
class GitHubError(Exception):
    pass


class MissingTokenError(GitHubError):
    pass


class RateLimitError(GitHubError):
    def __init__(self, message: str, reset_at: datetime | None = None):
        super().__init__(message)
        self.reset_at = reset_at


class ArtifactGoneError(GitHubError):
    pass


class GitHubClient:
    def __init__(self, token: str, repo: str, session: requests.Session | None = None,
                 api_url: str = GITHUB_API, timeout: float = 30):
        if not token:
            raise MissingTokenError("GITHUB_TOKEN is not set; artifact downloads require a token")
        self.repo = repo
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "banktest-dashboard",
        }

    def _request(self, url: str, params: dict | None = None, stream: bool = False):
        if not url.startswith("http"):
            url = f"{self.api_url}{url}"
        try:
            resp = self.session.get(url, headers=self.headers, params=params,
                                    timeout=self.timeout, stream=stream)
        except requests.RequestException as exc:
            raise GitHubError(f"network error calling GitHub: {exc}") from exc
        self._check(resp)
        return resp

    @staticmethod
    def _check(resp) -> None:
        status = resp.status_code
        if status < 400:
            return
        headers = resp.headers or {}
        body = ""
        try:
            body = resp.text[:300]
        except Exception:  # noqa: BLE001 - body is diagnostic only
            pass
        if status in (403, 429) and (
            headers.get("X-RateLimit-Remaining") == "0"
            or "Retry-After" in headers
            or "rate limit" in body.lower()
        ):
            reset_at = None
            if headers.get("X-RateLimit-Reset", "").isdigit():
                reset_at = datetime.fromtimestamp(int(headers["X-RateLimit-Reset"]), tz=timezone.utc)
            elif headers.get("Retry-After", "").isdigit():
                reset_at = datetime.fromtimestamp(time.time() + int(headers["Retry-After"]), tz=timezone.utc)
            when = f" until {reset_at:%Y-%m-%d %H:%M:%S} UTC" if reset_at else ""
            raise RateLimitError(f"GitHub API rate limit reached{when}", reset_at)
        if status == 401:
            raise GitHubError("GitHub rejected the token (401). Check GITHUB_TOKEN.")
        if status == 403:
            raise GitHubError("GitHub denied access (403). The token needs 'actions: read' on the repo.")
        if status == 404:
            raise GitHubError(f"not found (404): {resp.url}. Check GITHUB_REPOSITORY and the workflow file name.")
        if status == 410:
            raise ArtifactGoneError("artifact has expired or was deleted (410)")
        raise GitHubError(f"GitHub API error {status}: {body}")

    def list_workflow_runs(self, workflow: str = WORKFLOW_FILE, limit: int = 10) -> list[dict]:
        runs: list[dict] = []
        page = 1
        while len(runs) < limit:
            resp = self._request(
                f"/repos/{self.repo}/actions/workflows/{workflow}/runs",
                params={"status": "completed", "per_page": min(max(limit, 1), 100), "page": page},
            )
            batch = resp.json().get("workflow_runs") or []
            runs.extend(batch)
            if len(batch) < min(max(limit, 1), 100):
                break
            page += 1
        return runs[:limit]

    def list_run_artifacts(self, run_id) -> list[dict]:
        resp = self._request(f"/repos/{self.repo}/actions/runs/{run_id}/artifacts",
                             params={"per_page": 100})
        return resp.json().get("artifacts") or []

    def download_artifact(self, artifact: dict, dest: Path) -> Path:
        url = artifact.get("archive_download_url") or \
            f"/repos/{self.repo}/actions/artifacts/{artifact['id']}/zip"
        # requests drops the Authorization header on the cross-host redirect to blob storage.
        resp = self._request(url, stream=True)
        written = 0
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                written += len(chunk)
                if written > MAX_ARTIFACT_BYTES:
                    raise GitHubError("artifact exceeds the download size limit")
                fh.write(chunk)
        return dest


def safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract a zip, rejecting path traversal, symlinks and oversized content."""
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise IngestError(f"artifact contains a symlink: {info.filename}")
                target = (dest / info.filename).resolve()
                if dest not in target.parents:
                    raise IngestError(f"artifact entry escapes extraction dir: {info.filename}")
                total += info.file_size
                if total > MAX_EXTRACTED_BYTES:
                    raise IngestError("artifact is too large when extracted")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
    except zipfile.BadZipFile as exc:
        raise IngestError(f"artifact is not a valid zip: {exc}") from exc


@dataclass
class RunSyncResult:
    workflow_run_id: str
    status: str            # ingested | skipped | expired | no_artifact | invalid | error
    detail: str = ""
    run_id: str | None = None


@dataclass
class SyncReport:
    repo: str
    results: list[RunSyncResult] = field(default_factory=list)
    stopped: str | None = None   # set when sync aborted early (e.g. rate limit)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    def describe(self) -> str:
        parts = [f"{self.count(s)} {s}" for s in
                 ("ingested", "skipped", "expired", "no_artifact", "invalid", "error") if self.count(s)]
        text = f"{self.repo}: " + (", ".join(parts) if parts else "no completed workflow runs found")
        if self.stopped:
            text += f" — stopped early: {self.stopped}"
        return text


def _run_defaults(run: dict) -> dict:
    return {
        "run_id": _to_str(run.get("id")),
        "workflow_run_id": _to_str(run.get("id")),
        "workflow_run_url": run.get("html_url"),
        "commit_sha": run.get("head_sha"),
        "branch": run.get("head_branch"),
        "trigger": run.get("event"),
        "started_at": run.get("run_started_at") or run.get("created_at"),
        "finished_at": run.get("updated_at"),
    }


def sync_run(store: HistoryStore, client: GitHubClient, run: dict,
             artifact_name: str = ARTIFACT_NAME) -> RunSyncResult:
    wid = str(run.get("id"))
    artifacts = [a for a in client.list_run_artifacts(wid) if a.get("name") == artifact_name]
    if not artifacts:
        conclusion = run.get("conclusion") or "unknown"
        return RunSyncResult(wid, "no_artifact", f"no '{artifact_name}' artifact (run {conclusion})")
    live = [a for a in artifacts if not a.get("expired")]
    if not live:
        return RunSyncResult(wid, "expired", "artifact expired (Actions retention elapsed)")
    artifact = max(live, key=lambda a: a.get("created_at") or "")
    if (artifact.get("size_in_bytes") or 0) > MAX_ARTIFACT_BYTES:
        return RunSyncResult(wid, "error", "artifact larger than the download limit")

    with tempfile.TemporaryDirectory(prefix="banktest-artifact-") as tmp:
        zip_path = Path(tmp) / "artifact.zip"
        extract_dir = Path(tmp) / "extracted"
        try:
            client.download_artifact(artifact, zip_path)
        except ArtifactGoneError:
            return RunSyncResult(wid, "expired", "artifact expired or deleted")
        safe_extract(zip_path, extract_dir)
        result = ingest_reports_dir(store, extract_dir, source="github", defaults=_run_defaults(run))
    return RunSyncResult(wid, "ingested", result.describe(), result.run_id)


def sync_github(store: HistoryStore, token: str | None = None, repo: str | None = None,
                limit: int = 10, force: bool = False, workflow: str = WORKFLOW_FILE,
                artifact_name: str = ARTIFACT_NAME, client: GitHubClient | None = None,
                progress: Callable[[RunSyncResult], None] | None = None) -> SyncReport:
    """Download and ingest the `test-results` artifact of recent workflow runs.

    Raises MissingTokenError when no token is available and GitHubError when
    the run listing itself fails; per-run problems are reported in the result.
    """
    repo = repo or resolve_repo()
    client = client or GitHubClient(token or resolve_token(), repo)
    report = SyncReport(repo)
    try:
        runs = client.list_workflow_runs(workflow, limit)
    except RateLimitError as exc:
        report.stopped = str(exc)
        return report

    for run in runs:
        wid = str(run.get("id"))
        if not force and store.workflow_run_ingested(wid):
            outcome = RunSyncResult(wid, "skipped", "already in history")
        else:
            try:
                outcome = sync_run(store, client, run, artifact_name)
            except RateLimitError as exc:
                report.stopped = str(exc)
                break
            except IngestError as exc:
                outcome = RunSyncResult(wid, "invalid", str(exc))
            except GitHubError as exc:
                outcome = RunSyncResult(wid, "error", str(exc))
        report.results.append(outcome)
        if progress:
            progress(outcome)
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest BankTest results into the dashboard history DB.")
    parser.add_argument("--db", help="SQLite path (default: $BANKTEST_DB_PATH or dashboard/data/history.db)")
    sub = parser.add_subparsers(dest="command", required=True)

    local = sub.add_parser("local", help="ingest a local reports directory")
    local.add_argument("reports_dir", nargs="?", help="default: testing/reports")

    gh = sub.add_parser("github", help="ingest test-results artifacts from GitHub Actions")
    gh.add_argument("--limit", type=int, default=10, help="most recent completed runs to check (default 10)")
    gh.add_argument("--repo", help=f"owner/name (default: $GITHUB_REPOSITORY or {DEFAULT_REPO})")
    gh.add_argument("--workflow", default=WORKFLOW_FILE)
    gh.add_argument("--force", action="store_true", help="re-download runs already in history")

    prune = sub.add_parser("prune", help="delete all but the newest N runs from history")
    prune.add_argument("--keep", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    store = HistoryStore(args.db) if args.db else HistoryStore()

    if args.command == "local":
        try:
            result = ingest_reports_dir(store, Path(args.reports_dir) if args.reports_dir else None)
        except IngestError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(result.describe())
        print(f"history: {store.db_path}")
        return 0

    if args.command == "github":
        def show(r: RunSyncResult) -> None:
            print(f"  run {r.workflow_run_id}: {r.status}" + (f" — {r.detail}" if r.detail else ""))
        try:
            report = sync_github(store, repo=args.repo, limit=args.limit, force=args.force,
                                 workflow=args.workflow, progress=show)
        except MissingTokenError as exc:
            print(f"error: {exc}. Create a token with 'actions: read' and export GITHUB_TOKEN.",
                  file=sys.stderr)
            return 2
        except GitHubError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(report.describe())
        return 1 if report.stopped or report.count("error") else 0

    if args.command == "prune":
        deleted = store.prune(args.keep)
        print(f"deleted {len(deleted)} run(s); kept the newest {args.keep}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
