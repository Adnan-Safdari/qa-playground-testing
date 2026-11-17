import io
import zipfile
from pathlib import Path

import pytest

from ingest import (
    GitHubClient, GitHubError, IngestError, MissingTokenError, safe_extract, sync_github,
)

API = "https://api.github.com"
REPO = "owner/repo"


class FakeResp:
    def __init__(self, status=200, json_data=None, content=b"", headers=None, url=""):
        self.status_code = status
        self._json = json_data or {}
        self.content = content
        self.headers = headers or {}
        self.url = url
        self.text = content.decode(errors="ignore") if content else str(json_data or "")

    def json(self):
        return self._json

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None, stream=False):
        self.calls.append(url)
        assert headers["Authorization"] == "Bearer tok"
        resp = self.routes.get(url)
        if resp is None:
            return FakeResp(404, url=url)
        return resp


def zip_dir(src: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in src.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())
    return buf.getvalue()


def wf_run(run_id, sha="c" * 40):
    return {"id": run_id, "html_url": f"https://github.com/{REPO}/actions/runs/{run_id}", "head_sha": sha,
            "head_branch": "main", "event": "push", "run_started_at": "2026-11-12T08:00:00Z",
            "updated_at": "2026-11-12T08:05:00Z", "conclusion": "failure"}


def artifact(aid, expired=False):
    return {"id": aid, "name": "test-results", "expired": expired, "size_in_bytes": 1000,
            "created_at": "2026-11-12T08:05:00Z",
            "archive_download_url": f"{API}/repos/{REPO}/actions/artifacts/{aid}/zip"}


def make_client(routes):
    return GitHubClient("tok", REPO, session=FakeSession(routes))


def routes_for(fixtures, runs, artifacts_by_run, zips):
    routes = {f"{API}/repos/{REPO}/actions/workflows/selenium-tests.yml/runs": FakeResp(json_data={"workflow_runs": runs})}
    for rid, arts in artifacts_by_run.items():
        routes[f"{API}/repos/{REPO}/actions/runs/{rid}/artifacts"] = FakeResp(json_data={"artifacts": arts})
    for aid, content in zips.items():
        routes[f"{API}/repos/{REPO}/actions/artifacts/{aid}/zip"] = FakeResp(content=content)
    return routes


def test_sync_ingests_skips_and_reports_expired(store, fixtures):
    routes = routes_for(
        fixtures,
        runs=[wf_run(12345), wf_run(200), wf_run(300)],
        artifacts_by_run={12345: [artifact(1)], 200: [artifact(2, expired=True)], 300: []},
        zips={1: zip_dir(fixtures / "reports_fail")},
    )
    client = make_client(routes)
    report = sync_github(store, repo=REPO, limit=5, client=client)
    statuses = {r.workflow_run_id: r.status for r in report.results}
    assert statuses == {"12345": "ingested", "200": "expired", "300": "no_artifact"}
    run = store.get_run("12345")
    assert run["source"] == "github"
    assert run["branch"] == "demo/regression"  # file value wins over API default
    assert store.get_results("12345")["screenshot"].notna().sum() == 1

    again = sync_github(store, repo=REPO, limit=5, client=client)
    assert {r.workflow_run_id: r.status for r in again.results}["12345"] == "skipped"


def test_api_metadata_fills_gaps(store, tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "results.json").write_text('{"schema_version": 1, "tests": [{"tc_id": "A", "outcome": "passed"}]}')
    routes = routes_for(None, [wf_run(42)], {42: [artifact(9)]}, {9: zip_dir(reports)})
    sync_github(store, repo=REPO, limit=1, client=make_client(routes))
    run = store.get_run("42")
    assert run["commit_sha"] == "c" * 40 and run["trigger"] == "push"
    assert run["workflow_run_url"].endswith("/runs/42")


def test_invalid_artifact_is_reported_not_raised(store, tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "results.json").write_text('{"schema_version": 7}')
    routes = routes_for(None, [wf_run(5)], {5: [artifact(5)]}, {5: zip_dir(reports)})
    report = sync_github(store, repo=REPO, limit=1, client=make_client(routes))
    assert report.results[0].status == "invalid"
    assert "schema_version" in report.results[0].detail


def test_rate_limit_stops_sync(store):
    routes = {
        f"{API}/repos/{REPO}/actions/workflows/selenium-tests.yml/runs": FakeResp(
            json_data={"workflow_runs": [wf_run(1), wf_run(2)]}),
        f"{API}/repos/{REPO}/actions/runs/1/artifacts": FakeResp(
            403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1900000000"}),
    }
    report = sync_github(store, repo=REPO, limit=2, client=make_client(routes))
    assert report.stopped and "rate limit" in report.stopped
    assert report.results == []


def test_listing_rate_limited_returns_report(store):
    routes = {f"{API}/repos/{REPO}/actions/workflows/selenium-tests.yml/runs": FakeResp(429, headers={"Retry-After": "30"})}
    report = sync_github(store, repo=REPO, client=make_client(routes))
    assert "rate limit" in report.stopped


def test_auth_errors(store):
    with pytest.raises(MissingTokenError):
        GitHubClient("", REPO)
    routes = {f"{API}/repos/{REPO}/actions/workflows/selenium-tests.yml/runs": FakeResp(401)}
    with pytest.raises(GitHubError, match="401"):
        sync_github(store, repo=REPO, client=make_client(routes))


def test_expired_download_410(store, fixtures):
    routes = routes_for(fixtures, [wf_run(7)], {7: [artifact(7)]}, {})
    routes[f"{API}/repos/{REPO}/actions/artifacts/7/zip"] = FakeResp(410)
    report = sync_github(store, repo=REPO, limit=1, client=make_client(routes))
    assert report.results[0].status == "expired"


def test_safe_extract_rejects_traversal(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "x")
    zpath = tmp_path / "a.zip"
    zpath.write_bytes(buf.getvalue())
    with pytest.raises(IngestError, match="escapes"):
        safe_extract(zpath, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_safe_extract_bad_zip(tmp_path):
    zpath = tmp_path / "a.zip"
    zpath.write_bytes(b"not a zip")
    with pytest.raises(IngestError, match="valid zip"):
        safe_extract(zpath, tmp_path / "out")
