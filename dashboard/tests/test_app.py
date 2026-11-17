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
    assert any("Local ingest failed" in e.value for e in at.error)


def test_run_all_blocked_when_app_down(env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://127.0.0.1:9")  # nothing listens here
    at = run_app()
    assert next(b for b in at.button if b.label == "Trigger CI run").disabled  # no token
    next(b for b in at.button if b.label == "Run all tests").click().run()
    assert not at.exception
    assert any("Start the app first" in e.value for e in at.error)
    assert not next(b for b in at.button if b.label == "Run all tests").disabled


def test_renders_with_history(env, fixtures, monkeypatch):
    store = HistoryStore(env / "history.db")
    ingest_reports_dir(store, fixtures / "reports_pass")
    ingest_reports_dir(store, fixtures / "reports_fail")
    monkeypatch.setenv("BANKTEST_CATALOGUE_PATH", str(fixtures / "test_cases.json"))
    at = run_app()
    page = " ".join(m.value for m in at.markdown)
    assert "QA Command Center" in page and "FAILED" in page
    assert "60.0%" in page and "QUALITY GATE FAILED" in page and "SB-TR-01" in page
    labels = {m.label: m.value for m in at.metric}  # Execution Details defaults to the latest run
    assert labels["Failed"] == "1" and labels["Critical failures"] == "1"
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
    assert labels["Total"] == "2"
    assert "50.0%" in " ".join(m.value for m in at.markdown)
