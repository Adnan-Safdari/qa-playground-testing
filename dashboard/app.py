"""BankTest QA dashboard — Streamlit UI over the SQLite execution history.

Run:  streamlit run dashboard/app.py
All numbers come from ingested pytest runs (results.json) and the
test-case catalogue (testing/test_cases.json). Nothing is hardcoded.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

import analytics as an
import charts
from ingest import (
    DEFAULT_REPO,
    GitHubError,
    IngestError,
    MissingTokenError,
    catalogue_path_from_env,
    ingest_reports_dir,
    load_catalogue,
    reports_dir_from_env,
    resolve_token,
    sync_github,
)
from storage import REPORT_FILES, HistoryStore

st.set_page_config(page_title="BankTest QA Dashboard", page_icon=":material/fact_check:", layout="wide")

EMPTY_STATE = "No test runs yet — run `pytest` in `testing/` or ingest from GitHub."
OUTCOME_ICONS = {"passed": "✔", "failed": "✖", "error": "⚠", "skipped": "↷", "unknown": "?"}
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
CHART_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


# ---------------------------------------------------------------- data access
@st.cache_resource
def get_store(db_path: str | None) -> HistoryStore:
    return HistoryStore(db_path)


def store() -> HistoryStore:
    return get_store(os.environ.get("BANKTEST_DB_PATH"))


@st.cache_data(ttl=60, show_spinner=False)
def load_runs(db_path: str) -> pd.DataFrame:
    return store().list_runs()


@st.cache_data(ttl=60, show_spinner=False)
def load_results(db_path: str, run_id: str | None = None) -> pd.DataFrame:
    return store().get_results(run_id)


@st.cache_data(ttl=60, show_spinner=False)
def load_cases(path: str) -> tuple[list[dict], str | None]:
    return load_catalogue(path)


def _secret(name: str) -> str | None:
    try:
        return st.secrets.get(name)
    except Exception:  # no secrets.toml configured
        return None


def github_token() -> str | None:
    return resolve_token() or _secret("GITHUB_TOKEN")


def github_repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or _secret("GITHUB_REPOSITORY") or DEFAULT_REPO


def refresh() -> None:
    st.cache_data.clear()
    st.rerun()


def outcome_label(outcome) -> str:
    if not isinstance(outcome, str):
        return "—"
    return f"{OUTCOME_ICONS.get(outcome, '?')} {outcome.capitalize()}"


def status_badge(status: str) -> None:
    color, icon = {"PASSED": ("green", ":material/check_circle:"),
                   "FAILED": ("red", ":material/cancel:")}.get(status, ("gray", ":material/help:"))
    st.badge(status, icon=icon, color=color)


def commit_link(run: dict) -> str:
    sha = run.get("commit_sha")
    if not sha:
        return "—"
    if run.get("workflow_run_url") or run.get("source") == "github":
        return f"[`{sha[:10]}`](https://github.com/{github_repo()}/commit/{sha})"
    return f"`{sha[:10]}`"


def sort_by_priority(values) -> list:
    known = [p for p in PRIORITY_ORDER if p in values]
    return known + sorted(v for v in values if v not in PRIORITY_ORDER)


# ------------------------------------------------------------------- sidebar
def sidebar(runs: pd.DataFrame) -> None:
    sb = st.sidebar
    sb.title("BankTest")
    sb.caption("Continuous QA for the SecureBank demo app")

    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(sb, flash[0])(flash[1])

    sb.subheader("Ingest results")
    reports_dir = reports_dir_from_env()
    if sb.button("Ingest local results", icon=":material/upload_file:", width="stretch",
                 help=f"Read {reports_dir}/results.json into the history database."):
        try:
            result = ingest_reports_dir(store(), reports_dir)
            st.session_state["flash"] = ("success", result.describe())
        except IngestError as exc:
            st.session_state["flash"] = ("error", f"Local ingest failed: {exc}")
        refresh()

    token = github_token()
    repo = github_repo()
    limit = sb.number_input("GitHub runs to check", min_value=1, max_value=100, value=10, step=1)
    if sb.button("Sync from GitHub", icon=":material/cloud_download:", width="stretch",
                 disabled=not token,
                 help=f"Download the `test-results` artifact of recent selenium-tests.yml runs in {repo}."):
        with sb.status("Syncing from GitHub…", expanded=True) as status:
            try:
                report = sync_github(store(), token=token, repo=repo, limit=int(limit),
                                     progress=lambda r: status.write(f"run {r.workflow_run_id}: {r.status}"))
                kind = "warning" if report.stopped or report.count("error") else "success"
                st.session_state["flash"] = (kind, report.describe())
            except MissingTokenError as exc:
                st.session_state["flash"] = ("error", str(exc))
            except GitHubError as exc:
                st.session_state["flash"] = ("error", f"GitHub sync failed: {exc}")
        refresh()
    if not token:
        sb.caption("GitHub sync is disabled: set `GITHUB_TOKEN` (env or `.streamlit/secrets.toml`) "
                   "to a token with `actions: read` on the repository. Artifact downloads require "
                   "authentication even for public repos.")
    else:
        sb.caption(f"Repository: `{repo}`")

    sb.divider()
    sb.caption(f"History: {len(runs)} run(s) in `{store().db_path}`")
    sb.caption("GitHub artifacts expire after 30 days; this SQLite history and the copied "
               "screenshots/reports are the long-term record.")
    if sb.button("Reload data", icon=":material/refresh:", width="stretch"):
        refresh()


# ------------------------------------------------------------------ overview
def overview(runs: pd.DataFrame, cases: list[dict]) -> None:
    blocked = sum(1 for c in cases if (c.get("status") or "").lower() == "blocked")
    if runs.empty:
        st.info(EMPTY_STATE, icon=":material/info:")
        if cases:
            st.caption(f"Catalogue: {len(cases)} test cases, {blocked} blocked.")
        return

    latest = an.row_dict(runs.iloc[0])
    previous = an.row_dict(runs.iloc[1]) if len(runs) > 1 else None
    results = load_results(str(store().db_path), latest["run_id"])

    head = st.columns([3, 2])
    with head[0]:
        st.subheader("Latest run")
        status_badge(an.run_status(latest))
        if latest["critical_failed"]:
            st.badge(f"Quality gate failed: {latest['critical_failed']} critical failure(s)",
                     icon=":material/gpp_bad:", color="red")
    with head[1]:
        st.markdown(
            f"**Started** {an.fmt_ts(latest['started_at'])}  \n"
            f"**Branch** `{latest.get('branch') or '—'}` · **Commit** {commit_link(latest)}  \n"
            f"**Trigger** {latest.get('trigger') or '—'} · **Source** {latest['source']}"
        )
        if latest.get("workflow_run_url"):
            st.link_button("Open workflow run", latest["workflow_run_url"], icon=":material/open_in_new:")

    def delta(key):
        return None if previous is None else latest[key] - previous[key]

    row1 = st.columns(7)
    row1[0].metric("Total", latest["total"], delta=delta("total"), delta_color="off")
    row1[1].metric("Passed", latest["passed"], delta=delta("passed"))
    row1[2].metric("Failed", latest["failed"], delta=delta("failed"), delta_color="inverse")
    row1[3].metric("Error", latest["error"], delta=delta("error"), delta_color="inverse")
    row1[4].metric("Skipped", latest["skipped"], delta=delta("skipped"), delta_color="off")
    row1[5].metric("Blocked", blocked if cases else "—",
                   help="Catalogue cases with status 'Blocked' (feature unavailable).")
    row1[6].metric("Pass rate", f"{latest['pass_rate']:.2f}%",
                   delta=None if previous is None else f"{latest['pass_rate'] - previous['pass_rate']:+.2f} pp",
                   help="passed / (total − skipped)")

    durations = results["duration_seconds"].dropna()
    row2 = st.columns(7)
    row2[0].metric("Run duration", an.fmt_duration(latest["duration_seconds"]))
    row2[1].metric("Avg test duration", an.fmt_duration(durations.mean() if len(durations) else None))
    row2[2].metric("Critical failures", latest["critical_failed"])
    row2[3].metric("Runs in history", len(runs))

    failing = results[results["outcome"].isin(an.FAILING)]
    if not failing.empty:
        st.subheader(f"Failures in this run ({len(failing)})")
        view = failing.assign(outcome=failing["outcome"].map(outcome_label))
        st.dataframe(
            view[["tc_id", "title", "module", "priority", "outcome", "message"]],
            hide_index=True, width="stretch",
            column_config={"tc_id": "ID", "title": "Title", "module": "Module", "priority": "Priority",
                           "outcome": "Outcome", "message": st.column_config.TextColumn("Message", width="large")},
        )
        st.caption("Tracebacks and screenshots: **Execution Details** tab.")

    st.subheader("Recent runs")
    recent = runs.head(15).copy()
    recent["status"] = recent.apply(an.run_status, axis=1)
    recent["started"] = recent["started_at"].map(an.fmt_ts)
    recent["commit"] = recent["commit_sha"].fillna("").str[:7]
    recent["duration"] = recent["duration_seconds"].map(an.fmt_duration)
    st.dataframe(
        recent[["started", "status", "branch", "commit", "trigger", "total", "passed", "failed",
                "error", "skipped", "pass_rate", "critical_failed", "duration", "workflow_run_url"]],
        hide_index=True, width="stretch",
        column_config={
            "started": "Started", "status": "Status", "branch": "Branch", "commit": "Commit",
            "trigger": "Trigger", "total": "Total", "passed": "Passed", "failed": "Failed",
            "error": "Error", "skipped": "Skipped", "critical_failed": "Critical fails",
            "duration": "Duration",
            "pass_rate": st.column_config.ProgressColumn("Pass rate", min_value=0, max_value=100, format="%.1f%%"),
            "workflow_run_url": st.column_config.LinkColumn("Workflow run", display_text="open"),
        },
    )


# ----------------------------------------------------------- test management
def test_management(cases: list[dict], catalogue_error: str | None, all_results: pd.DataFrame) -> None:
    if catalogue_error:
        st.error(f"Could not read the test-case catalogue: {catalogue_error}")
    if not cases:
        st.info(f"No test-case catalogue found at `{catalogue_path_from_env()}`. "
                "The test suite owner maintains it (APP_CONTRACT.md §5).", icon=":material/info:")
        return

    table = an.catalogue_table(cases, all_results)
    statuses = sorted(table["current_status"].unique())

    f = st.columns([2, 2, 2, 3])
    modules = f[0].multiselect("Module", sorted(table["module"].unique()))
    priorities = f[1].multiselect("Priority", sort_by_priority(table["priority"].unique()))
    chosen_status = f[2].multiselect("Current status", statuses)
    query = f[3].text_input("Search ID / title", placeholder="e.g. SB-TR or transfer")

    view = table
    if modules:
        view = view[view["module"].isin(modules)]
    if priorities:
        view = view[view["priority"].isin(priorities)]
    if chosen_status:
        view = view[view["current_status"].isin(chosen_status)]
    if query:
        q = query.lower()
        view = view[view["tc_id"].str.lower().str.contains(q, regex=False)
                    | view["title"].str.lower().str.contains(q, regex=False)]

    m = st.columns(6)
    m[0].metric("Cases shown", len(view))
    m[1].metric("Automated", int(view["automated"].sum()))
    m[2].metric("Passing", int((view["current_status"] == "Passed").sum()))
    m[3].metric("Failing", int(view["current_status"].isin(["Failed", "Error"]).sum()))
    m[4].metric("Blocked", int((view["current_status"] == "Blocked").sum()))
    m[5].metric("Not run", int((view["current_status"] == "Not run").sum()))

    display = view.assign(last_run=view["last_run_at"].map(an.fmt_ts) if "last_run_at" in view else "—")
    event = st.dataframe(
        display[["tc_id", "module", "title", "priority", "automated", "status", "current_status",
                 "last_run", "expected_result"]],
        hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
        key="catalogue_table",
        column_config={
            "tc_id": "ID", "module": "Module", "title": "Title", "priority": "Priority",
            "automated": st.column_config.CheckboxColumn("Automated"),
            "status": "Catalogue status", "current_status": "Current status", "last_run": "Last executed",
            "expected_result": st.column_config.TextColumn("Expected result", width="large"),
        },
    )

    unknown = sorted(set(all_results["tc_id"].dropna()) - set(table["tc_id"])) if not all_results.empty else []
    if unknown:
        st.caption(f"Executed test IDs missing from the catalogue: {', '.join(unknown)}")

    rows = event.selection.rows if event and event.selection else []
    if not rows:
        st.caption("Select a row to see the full test case.")
        return
    case = an.row_dict(view.iloc[rows[0]])
    st.subheader(f"{case['tc_id']} — {case['title']}")
    st.markdown(f"**Module** {case['module']} · **Priority** {case['priority']} · "
                f"**Catalogue status** {case['status']} · **Current status** {case['current_status']}")
    c = st.columns(2)
    with c[0]:
        st.markdown(f"**Objective**  \n{case.get('objective') or '—'}")
        st.markdown(f"**Preconditions**  \n{case.get('preconditions') or '—'}")
        st.markdown(f"**Test data**  \n{case.get('test_data') or '—'}")
    with c[1]:
        steps = case.get("steps") or []
        st.markdown("**Steps**  \n" + ("\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)) or "—"))
        st.markdown(f"**Expected result**  \n{case.get('expected_result') or '—'}")
        if case.get("notes"):
            st.markdown(f"**Notes**  \n{case['notes']}")
    if isinstance(case.get("last_message"), str) and case["current_status"] in ("Failed", "Error"):
        st.error(f"Latest failure ({an.fmt_ts(case['last_run_at'])}): {case['last_message']}")


# --------------------------------------------------------- execution details
def run_label(run: dict) -> str:
    sha = (run["commit_sha"] or "")[:7]
    parts = [an.fmt_ts(run["started_at"]), an.run_status(run), run["branch"] or "", sha]
    return " · ".join(p for p in parts if p)


def execution_details(runs: pd.DataFrame) -> None:
    if runs.empty:
        st.info(EMPTY_STATE, icon=":material/info:")
        return
    labels = {row["run_id"]: run_label(an.row_dict(row)) for _, row in runs.iterrows()}
    run_id = st.selectbox("Run", list(labels), format_func=lambda rid: labels[rid])
    run = store().get_run(run_id)
    results = load_results(str(store().db_path), run_id)

    status_badge(an.run_status(run))
    meta = st.columns(3)
    meta[0].markdown(f"**Run ID** `{run['run_id']}`  \n**Started** {an.fmt_ts(run['started_at'])}  \n"
                     f"**Finished** {an.fmt_ts(run['finished_at'])}  \n"
                     f"**Duration** {an.fmt_duration(run['duration_seconds'])}")
    meta[1].markdown(f"**Commit** {commit_link(run)}  \n**Branch** `{run.get('branch') or '—'}`  \n"
                     f"**Trigger** {run.get('trigger') or '—'}  \n**Source** {run['source']}")
    headless = {1: "yes", 0: "no"}.get(run.get("headless"), "—")
    meta[2].markdown(f"**Base URL** {run.get('base_url') or '—'}  \n**Browser** {run.get('browser') or '—'}  \n"
                     f"**Headless** {headless}")
    if run.get("workflow_run_url"):
        meta[2].link_button("Open workflow run", run["workflow_run_url"], icon=":material/open_in_new:")

    m = st.columns(6)
    for col, (label, key) in zip(m, [("Total", "total"), ("Passed", "passed"), ("Failed", "failed"),
                                     ("Error", "error"), ("Skipped", "skipped"), ("Critical failures", "critical_failed")]):
        col.metric(label, run[key])

    downloads = [(name, store().artifact_path(run_id, name)) for name in REPORT_FILES]
    downloads = [(n, p) for n, p in downloads if p]
    if downloads:
        cols = st.columns(len(downloads))
        mime = {"report.html": "text/html", "junit.xml": "application/xml", "results.json": "application/json"}
        for col, (name, path) in zip(cols, downloads):
            col.download_button(f"Download {name}", data=path.read_bytes(), file_name=f"{run_id}-{name}",
                                mime=mime[name], icon=":material/download:", width="stretch")
    else:
        st.caption("No report files were stored for this run.")

    if results.empty:
        st.warning("This run has no per-test results.")
        return

    st.subheader("Test results")
    outcomes = sorted(results["outcome"].unique())
    f = st.columns(2)
    chosen = f[0].multiselect("Outcome", outcomes, key="exec_outcome")
    modules = f[1].multiselect("Module", sorted(results["module"].dropna().unique()), key="exec_module")
    view = results
    if chosen:
        view = view[view["outcome"].isin(chosen)]
    if modules:
        view = view[view["module"].isin(modules)]
    st.dataframe(
        view.assign(outcome=view["outcome"].map(outcome_label))[
            ["tc_id", "title", "module", "priority", "outcome", "duration_seconds", "nodeid", "message"]],
        hide_index=True, width="stretch",
        column_config={
            "tc_id": "ID", "title": "Title", "module": "Module", "priority": "Priority", "outcome": "Outcome",
            "duration_seconds": st.column_config.NumberColumn("Duration", format="%.2f s"),
            "nodeid": "Pytest node", "message": "Message",
        },
    )
    with st.expander("Duration by test"):
        st.plotly_chart(charts.run_test_durations(view), width="stretch", config=CHART_CONFIG)

    failing = results[results["outcome"].isin(an.FAILING)]
    st.subheader(f"Failure details ({len(failing)})")
    if failing.empty:
        st.success("No failed or errored tests in this run.", icon=":material/check_circle:")
    for i, (_, row) in enumerate(failing.iterrows()):
        t = an.row_dict(row)
        title = f"{t['tc_id'] or t['nodeid']} — {t['title'] or ''} ({t['outcome']})"
        with st.expander(title, expanded=i == 0):
            st.markdown(f"**Module** {t['module'] or '—'} · **Priority** {t['priority'] or '—'} · "
                        f"**Duration** {an.fmt_duration(t['duration_seconds'])} · `{t['nodeid'] or ''}`")
            st.error(t["message"] or "No failure message recorded.")
            if t["traceback"]:
                st.code(t["traceback"], language="python", wrap_lines=False)
            shot = store().artifact_path(run_id, t["screenshot"])
            if shot:
                st.image(str(shot), caption=f"Failure screenshot: {t['screenshot']}")
                st.download_button("Download screenshot", data=shot.read_bytes(), file_name=shot.name,
                                   mime="image/png", key=f"shot-{run_id}-{t['seq']}")
            else:
                st.caption("No screenshot captured for this failure.")


# -------------------------------------------------------- history & analytics
def history(runs: pd.DataFrame, all_results: pd.DataFrame) -> None:
    if runs.empty:
        st.info(EMPTY_STATE, icon=":material/info:")
        return
    chrono = an.runs_chronological(runs)

    f = st.columns([2, 3])
    branches = sorted(chrono["branch"].dropna().unique())
    chosen_branches = f[0].multiselect("Branch", branches)
    if chosen_branches:
        chrono = chrono[chrono["branch"].isin(chosen_branches)]
    if len(chrono) > 2:
        window = f[1].slider("Most recent runs", min_value=2, max_value=len(chrono), value=min(len(chrono), 30))
        chrono = chrono.tail(window)
    if chrono.empty:
        st.info("No runs match the filter.")
        return
    results = all_results[all_results["run_id"].isin(chrono["run_id"])]
    if len(chrono) == 1:
        st.caption("Only one run in view — trends need at least two runs.")

    c = st.columns(2)
    with c[0]:
        st.markdown("**Outcomes per run**")
        st.plotly_chart(charts.outcome_trend(chrono), width="stretch", config=CHART_CONFIG)
    with c[1]:
        st.markdown("**Pass rate per run**")
        st.plotly_chart(charts.pass_rate_trend(chrono), width="stretch", config=CHART_CONFIG)

    c = st.columns(2)
    with c[0]:
        st.markdown("**Failing results by module**")
        by_module = an.failures_by_module(results)
        if by_module.empty:
            st.success("No failures in the selected runs.", icon=":material/check_circle:")
        else:
            st.plotly_chart(charts.module_failures(by_module), width="stretch", config=CHART_CONFIG)
    with c[1]:
        st.markdown("**Run duration**")
        st.plotly_chart(charts.duration_trend(chrono), width="stretch", config=CHART_CONFIG)

    st.markdown("**Most frequently failing test cases**")
    stats = an.failure_stats(results)
    if stats.empty:
        st.success("No test case failed in the selected runs.", icon=":material/check_circle:")
    else:
        stats = stats.assign(last_failure_at=stats["last_failure_at"].map(an.fmt_ts))
        st.dataframe(
            stats, hide_index=True, width="stretch",
            column_config={
                "tc_id": "ID", "title": "Title", "module": "Module", "priority": "Priority",
                "runs": st.column_config.NumberColumn("Executions", help="Runs where the case ran (not skipped)"),
                "failures": "Failures",
                "failure_rate": st.column_config.ProgressColumn("Failure rate", min_value=0, max_value=100,
                                                                format="%.0f%%"),
                "flips": st.column_config.NumberColumn("Pass↔fail flips",
                                                       help="Outcome changes between consecutive runs"),
                "pattern": st.column_config.TextColumn(
                    "Pattern", help="Flaky = both passed and failed on the same commit. "
                                    "Failing now / Recovered = latest execution failed / passed."),
                "last_failure_at": "Last failure", "last_message": "Last failure message",
            },
        )

    st.markdown("**Slowest test cases (average duration)**")
    slow = an.slowest_tests(results)
    if not slow.empty:
        st.dataframe(slow, hide_index=True, width="stretch", column_config={
            "tc_id": "ID", "title": "Title", "runs": "Runs",
            "avg_seconds": st.column_config.NumberColumn("Avg", format="%.2f s"),
            "max_seconds": st.column_config.NumberColumn("Max", format="%.2f s"),
        })


# ---------------------------------------------------------------------- main
def main() -> None:
    db = str(store().db_path)
    runs = load_runs(db)
    cases, catalogue_error = load_cases(str(catalogue_path_from_env()))
    sidebar(runs)

    st.title("BankTest — QA Execution Dashboard")
    st.caption("Selenium + Pytest regression results for the SecureBank demo app. "
               "All figures come from ingested test runs; nothing here is sample data.")

    all_results = load_results(db) if not runs.empty else store().get_results().iloc[0:0]
    tabs = st.tabs(["Overview", "Test Management", "Execution Details", "History & Analytics"])
    with tabs[0]:
        overview(runs, cases)
    with tabs[1]:
        test_management(cases, catalogue_error, all_results)
    with tabs[2]:
        execution_details(runs)
    with tabs[3]:
        history(runs, all_results)


main()
