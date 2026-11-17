import pandas as pd

import analytics as an
from ingest import ingest_reports_dir, load_catalogue


def results_frame(rows):
    base = {"title": "t", "module": "M", "priority": "High", "nodeid": None, "message": None,
            "duration_seconds": 1.0, "seq": 0}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_run_status():
    assert an.run_status({"total": 0, "failed": 0, "error": 0}) == "NO TESTS"
    assert an.run_status({"total": 3, "failed": 0, "error": 1}) == "FAILED"
    assert an.run_status({"total": 3, "failed": 0, "error": 0}) == "PASSED"


def test_failure_patterns():
    rows = []
    # A: pass -> fail -> pass on different commits = recovered regression, not flaky
    for i, (o, sha) in enumerate([("passed", "c1"), ("failed", "c2"), ("passed", "c3")]):
        rows.append({"run_id": f"r{i}", "tc_id": "A", "outcome": o, "run_commit_sha": sha,
                     "run_started_at": f"2026-11-1{i}T00:00:00Z"})
    # B: fails and passes on the same commit = flaky
    for i, o in enumerate(["failed", "passed"]):
        rows.append({"run_id": f"r{i}", "tc_id": "B", "outcome": o, "run_commit_sha": "c1",
                     "run_started_at": f"2026-11-1{i}T00:00:00Z"})
    # C: always errors
    rows.append({"run_id": "r0", "tc_id": "C", "outcome": "error", "run_commit_sha": "c1",
                 "run_started_at": "2026-11-10T00:00:00Z"})
    # D: never fails -> excluded
    rows.append({"run_id": "r0", "tc_id": "D", "outcome": "passed", "run_commit_sha": "c1",
                 "run_started_at": "2026-11-10T00:00:00Z"})
    stats = an.failure_stats(results_frame(rows)).set_index("tc_id")
    assert stats.loc["A", "pattern"] == "Recovered" and stats.loc["A", "flips"] == 2
    assert stats.loc["B", "pattern"] == "Flaky"
    assert stats.loc["C", "pattern"] == "Always failing"
    assert "D" not in stats.index


def test_worst_outcome_per_case_within_run():
    df = results_frame([
        {"run_id": "r", "tc_id": "P", "outcome": "passed", "run_commit_sha": "c", "run_started_at": "2026-11-10T00:00:00Z"},
        {"run_id": "r", "tc_id": "P", "outcome": "failed", "run_commit_sha": "c", "run_started_at": "2026-11-10T00:00:00Z"},
    ])
    assert an.latest_status_by_case(df).iloc[0]["latest_outcome"] == "failed"


def test_catalogue_table_and_module_failures(store, fixtures):
    ingest_reports_dir(store, fixtures / "reports_pass")
    ingest_reports_dir(store, fixtures / "reports_fail")
    cases, _ = load_catalogue(fixtures / "test_cases.json")
    results = store.get_results()
    table = an.catalogue_table(cases, results).set_index("tc_id")
    assert table.loc["SB-TR-01", "current_status"] == "Failed"   # latest run failed it
    assert table.loc["SB-PR-01", "current_status"] == "Passed"   # skipped earlier, passed latest
    assert table.loc["SB-OA-09", "current_status"] == "Blocked"
    mods = an.failures_by_module(results).set_index("module")
    assert mods.loc["Money Transfer", "failed"] == 1 and mods.loc["Logout", "error"] == 1
    runs = an.runs_chronological(store.list_runs())
    assert list(runs["run_id"]) == ["local-20261110T100000Z", "12345"]
    assert list(runs["status"]) == ["PASSED", "FAILED"]
    slow = an.slowest_tests(results).set_index("tc_id")
    assert slow.index[0] == "SB-TR-01" and slow.loc["SB-PR-01", "avg_seconds"] == 4.0  # skipped run excluded


def test_formatters():
    assert an.fmt_duration(None) == "—"
    assert an.fmt_duration(4.21) == "4.2s"
    assert an.fmt_duration(190.2) == "3m 10s"
    assert an.fmt_ts("2026-11-17T12:00:00Z") == "2026-11-17 12:00 UTC"
    assert an.fmt_ts(None) == "—"
