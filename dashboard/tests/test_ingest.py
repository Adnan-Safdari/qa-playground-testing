import json

import pytest

from ingest import (
    IngestError, ingest_reports_dir, load_catalogue, normalise_outcome, normalise_results,
    pass_rate, read_results_file,
)


def write(tmp_path, data, name="results.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data) if not isinstance(data, str) else data)
    return path


def test_read_rejects_bad_schema(tmp_path):
    with pytest.raises(IngestError, match="unsupported schema_version"):
        read_results_file(write(tmp_path, {"schema_version": 2}))
    with pytest.raises(IngestError, match="missing schema_version"):
        read_results_file(write(tmp_path, {"run": {}}))
    with pytest.raises(IngestError, match="not valid JSON"):
        read_results_file(write(tmp_path, "{nope"))
    with pytest.raises(IngestError, match="JSON object"):
        read_results_file(write(tmp_path, [1, 2]))
    with pytest.raises(IngestError, match="not found"):
        read_results_file(tmp_path / "missing.json")


def test_normalise_fixture_counts(fixtures):
    run, tests = normalise_results(read_results_file(fixtures / "reports_fail/results.json"))
    assert run["run_id"] == "12345"
    assert (run["total"], run["passed"], run["failed"], run["error"], run["skipped"]) == (5, 3, 1, 1, 0)
    assert run["pass_rate"] == 60.0
    assert run["critical_failed"] == 1
    assert tests[1]["screenshot"].startswith("screenshots/")


def test_pass_rate_formula():
    assert pass_rate(23, 25, 1) == 95.83
    assert pass_rate(0, 2, 2) == 0.0


def test_outcome_aliases():
    assert normalise_outcome("PASSED") == "passed"
    assert normalise_outcome("xfailed") == "skipped"
    assert normalise_outcome(None) == "unknown"
    assert normalise_outcome("weird") == "unknown"


def test_missing_fields_are_tolerated():
    run, tests = normalise_results({"schema_version": 1, "run": {"started_at": "2026-11-17T12:00:00Z"},
                                    "tests": [{"outcome": "passed"}, "junk", {"tc_id": "X", "duration_seconds": "abc"}]})
    assert run["run_id"] == "local-20261117T120000Z"
    assert run["total"] == 2 and run["passed"] == 1
    assert tests[1]["duration_seconds"] is None and tests[1]["outcome"] == "unknown"
    assert run["duration_seconds"] == 0.0


def test_no_identity_raises():
    with pytest.raises(IngestError, match="identify the run"):
        normalise_results({"schema_version": 1})


def test_summary_used_when_no_tests():
    run, tests = normalise_results({"schema_version": 1, "run": {"run_id": "r1"},
                                    "summary": {"total": 4, "passed": 3, "failed": 1, "critical_failed": 1}})
    assert tests == [] and run["total"] == 4 and run["failed"] == 1 and run["pass_rate"] == 75.0


def test_defaults_only_fill_missing():
    run, _ = normalise_results({"schema_version": 1, "run": {"branch": "feature"}},
                               defaults={"run_id": "99", "branch": "main", "commit_sha": "abc",
                                         "started_at": "2026-11-17T10:00:00.000+00:00"})
    assert run["run_id"] == "99" and run["branch"] == "feature" and run["commit_sha"] == "abc"
    assert run["started_at"] == "2026-11-17T10:00:00Z"


def test_ingest_copies_artifacts_and_is_idempotent(store, fixtures):
    first = ingest_reports_dir(store, fixtures / "reports_fail")
    assert not first.replaced and first.failed == 1
    second = ingest_reports_dir(store, fixtures / "reports_fail")
    assert second.replaced
    runs = store.list_runs()
    assert len(runs) == 1
    results = store.get_results("12345")
    assert len(results) == 5
    shot = results.loc[results["tc_id"] == "SB-TR-01", "screenshot"].iloc[0]
    assert store.artifact_path("12345", shot).read_bytes().startswith(b"\x89PNG")
    assert store.artifact_path("12345", "report.html") is not None
    assert store.artifact_path("12345", "results.json") is not None
    assert store.artifact_path("12345", "junit.xml") is None  # not in this fixture


def test_missing_or_unsafe_screenshot_is_dropped(store, tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (tmp_path / "secret.png").write_bytes(b"x")
    write(reports, {"schema_version": 1, "run": {"run_id": "r"}, "tests": [
        {"tc_id": "A", "outcome": "failed", "screenshot": "../secret.png"},
        {"tc_id": "B", "outcome": "failed", "screenshot": "screenshots/missing.png"},
    ]})
    ingest_reports_dir(store, reports)
    assert store.get_results("r")["screenshot"].isna().all()


def test_ingest_errors_for_missing_input(store, tmp_path):
    with pytest.raises(IngestError, match="not found"):
        ingest_reports_dir(store, tmp_path / "nope")
    with pytest.raises(IngestError, match="no results.json"):
        ingest_reports_dir(store, tmp_path)


def test_load_catalogue(fixtures, tmp_path):
    cases, err = load_catalogue(fixtures / "test_cases.json")
    assert err is None
    assert len(cases) == 6  # junk entries skipped
    tr02 = next(c for c in cases if c["tc_id"] == "SB-TR-02")
    assert tr02["steps"] == ["Enter 0"]
    assert load_catalogue(tmp_path / "none.json") == ([], None)
    bad = write(tmp_path, "{", "bad.json")
    assert load_catalogue(bad)[1]
