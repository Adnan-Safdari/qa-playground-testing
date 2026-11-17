"""Render the Streamlit app headlessly (AppTest) against temp databases."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ingest import ingest_reports_dir
from storage import HistoryStore

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("BANKTEST_DB_PATH", str(tmp_path / "history.db"))
    monkeypatch.setenv("BANKTEST_REPORTS_DIR", str(tmp_path / "no-reports"))
    monkeypatch.setenv("BANKTEST_CATALOGUE_PATH", str(tmp_path / "no-catalogue.json"))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return tmp_path


def run_app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_empty_state(env):
    at = run_app()
    assert any("No test runs yet" in i.value for i in at.info)
    sync = next(b for b in at.sidebar.button if b.label == "Sync from GitHub")
    assert sync.disabled


def test_local_ingest_button_reports_missing_dir(env):
    at = run_app()
    next(b for b in at.sidebar.button if b.label == "Ingest local results").click().run()
    assert not at.exception
    assert any("Local ingest failed" in e.value for e in at.sidebar.error)


def test_renders_with_history(env, fixtures, monkeypatch):
    store = HistoryStore(env / "history.db")
    ingest_reports_dir(store, fixtures / "reports_pass")
    ingest_reports_dir(store, fixtures / "reports_fail")
    monkeypatch.setenv("BANKTEST_CATALOGUE_PATH", str(fixtures / "test_cases.json"))
    at = run_app()
    labels = {m.label: m.value for m in at.metric}
    assert labels["Failed"] == "1" and labels["Pass rate"] == "60.00%" and labels["Blocked"] == "1"
    # pick the older run in Execution Details and re-render
    at.selectbox[0].select_index(1).run()
    assert not at.exception


def test_renders_sparse_run(env):
    reports = env / "sparse"
    reports.mkdir()
    (reports / "results.json").write_text(
        '{"schema_version": 1, "run": {"run_id": "bare"}, '
        '"tests": [{"outcome": "failed"}, {"tc_id": "X", "outcome": "passed"}]}')
    ingest_reports_dir(HistoryStore(env / "history.db"), reports)
    at = run_app()
    labels = {m.label: m.value for m in at.metric}
    assert labels["Total"] == "2" and labels["Pass rate"] == "50.00%"
