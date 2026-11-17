from ingest import ingest_reports_dir
from storage import safe_dirname


def test_runs_newest_first_and_prune(store, fixtures):
    ingest_reports_dir(store, fixtures / "reports_fail")
    ingest_reports_dir(store, fixtures / "reports_pass")
    runs = store.list_runs()
    assert list(runs["run_id"]) == ["12345", "local-20261110T100000Z"]
    assert store.workflow_run_ingested("12345")
    assert not store.workflow_run_ingested("777")
    deleted = store.prune(keep_last=1)
    assert deleted == ["local-20261110T100000Z"]
    assert not store.run_dir("local-20261110T100000Z").exists()
    assert store.get_results("local-20261110T100000Z").empty


def test_results_joined_with_run_metadata(store, fixtures):
    ingest_reports_dir(store, fixtures / "reports_pass", source="local")
    res = store.get_results()
    assert set(res["run_started_at"]) == {"2026-11-10T10:00:00Z"}
    assert list(res["seq"]) == list(range(5))
    assert store.get_run("local-20261110T100000Z")["headless"] == 1


def test_safe_dirname():
    assert safe_dirname("../../etc") == "etc"
    assert safe_dirname("local-2026:11") == "local-2026_11"
    assert safe_dirname("..") == "run"


def test_artifact_path_rejects_traversal(store, fixtures):
    ingest_reports_dir(store, fixtures / "reports_fail")
    assert store.artifact_path("12345", "../../history.db") is None
    assert store.artifact_path("12345", None) is None
