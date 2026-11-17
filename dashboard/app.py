"""BankTest QA Command Center — Streamlit UI over the SQLite execution history.

Run:  streamlit run dashboard/app.py
All numbers come from ingested pytest runs (results.json) and the
test-case catalogue (testing/test_cases.json). Nothing is hardcoded.
"""

from __future__ import annotations

import html
import os
import time

import pandas as pd
import streamlit as st

import analytics as an
import charts
import runner
from ingest import (
    DEFAULT_REPO,
    GitHubError,
    IngestError,
    MissingTokenError,
    WORKFLOW_FILE,
    catalogue_path_from_env,
    ingest_reports_dir,
    load_catalogue,
    reports_dir_from_env,
    resolve_token,
    sync_github,
)
from storage import REPORT_FILES, HistoryStore

st.set_page_config(page_title="BankTest QA Command Center", page_icon=":material/fact_check:", layout="wide")

EMPTY_STATE = "No test runs yet — run `pytest` in `testing/` or ingest from GitHub."
OUTCOME_CHIPS = {"passed": "🟢 Passed", "failed": "🔴 Failed", "error": "🟠 Error",
                 "skipped": "⚪ Skipped", "unknown": "⚫ Unknown"}
STATUS_CHIPS = {"Passed": "🟢 Passed", "Failed": "🔴 Failed", "Error": "🟠 Error", "Skipped": "⚪ Skipped",
                "Unknown": "⚫ Unknown", "Blocked": "⛔ Blocked", "Not applicable": "➖ Not applicable",
                "Not run": "◻️ Not run", "Manual": "✋ Manual"}
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
CHART_CONFIG = {"displaylogo": False, "displayModeBar": False}
TONES = {"good": "#0ca30c", "bad": "#d03b3b", "warn": "#e8a200", "neutral": "#7f22fe"}

CSS = """
<style>
.bt-header{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:0 0 2px}
.bt-title{font-size:2rem;font-weight:750;color:#1f1d2b;margin:0;line-height:1.3}
.bt-title span{color:#7f22fe}
.bt-pill{padding:3px 12px;border-radius:999px;font-weight:700;font-size:.78rem;letter-spacing:.05em;color:#fff}
.bt-meta{color:#6b6880;font-size:.9rem;margin-bottom:10px}
.bt-meta code{font-size:.85rem}
.kpi{background:#fff;border:1px solid #ece9f5;border-top:4px solid var(--tone);border-radius:12px;
     padding:12px 14px;min-height:112px}
.kpi-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;color:#6b6880;font-weight:600}
.kpi-value{font-size:1.75rem;font-weight:750;color:#1f1d2b;line-height:1.25}
.kpi-sub{font-size:.8rem;color:#6b6880}
.d-good{color:#0a7d0a;font-weight:600}.d-bad{color:#c22f2f;font-weight:600}.d-flat{color:#6b6880}
.gate{border-radius:12px;padding:12px 16px;border:1px solid;margin:4px 0 8px}
.gate-pass{background:#effaef;border-color:#bfe6bf}.gate-fail{background:#fdf0f0;border-color:#f1c4c4}
.gate b{font-size:1.05rem}
.chip{display:inline-block;padding:1px 9px;border-radius:999px;font-size:.72rem;font-weight:650;margin-right:6px}
.p-critical{background:#fde8e8;color:#b42323}.p-high{background:#fff1e0;color:#a65300}
.p-medium{background:#f1ecff;color:#5b17c9}.p-low,.p-other{background:#eef0f3;color:#4b5563}
.o-failed{background:#fde8e8;color:#b42323}.o-error{background:#fff1e0;color:#a65300}
</style>
"""


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


def flash(kind: str, text: str) -> None:
    """Queue a message shown at the top of the page after the next rerun."""
    st.session_state["flash"] = (kind, text)


def outcome_label(outcome) -> str:
    return OUTCOME_CHIPS.get(outcome, "—") if isinstance(outcome, str) else "—"


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


def by_priority(df: pd.DataFrame, *extra: str) -> pd.DataFrame:
    if df.empty:
        return df
    return (df.assign(_rank=df["priority"].map(an.priority_rank))
              .sort_values(["_rank", *extra], kind="stable").drop(columns="_rank"))


def priority_chip(priority) -> str:
    p = str(priority or "—")
    cls = f"p-{p.lower()}" if p.lower() in an.PRIORITY_RANK else "p-other"
    return f'<span class="chip {cls}">{html.escape(p)}</span>'


# ------------------------------------------------------------------- sidebar
def sidebar(runs: pd.DataFrame) -> dict:
    sb = st.sidebar
    sb.title("BankTest")
    sb.caption("Continuous QA for the SecureBank demo app")

    sb.subheader("Run settings")
    base_url = sb.text_input("App base URL", value=os.environ.get("BASE_URL", "http://localhost:3000"),
                             help="Local runs check <base>/bank/login before starting pytest.")
    branch = sb.text_input("CI branch", value="main", help="Ref for 'Trigger CI run on GitHub'.")

    sb.subheader("Ingest results")
    reports_dir = reports_dir_from_env()
    if sb.button("Ingest local results", icon=":material/upload_file:", width="stretch",
                 help=f"Read {reports_dir}/results.json into the history database."):
        try:
            flash("success", ingest_reports_dir(store(), reports_dir).describe())
        except IngestError as exc:
            flash("error", f"Local ingest failed: {exc}")
        refresh()

    token = github_token()
    repo = github_repo()
    limit = sb.number_input("GitHub runs to check", min_value=1, max_value=100, value=10, step=1)
    if sb.button("Sync from GitHub", icon=":material/cloud_download:", width="stretch",
                 disabled=not token,
                 help=f"Download the `test-results` artifact of recent {WORKFLOW_FILE} runs in {repo}."):
        with sb.status("Syncing from GitHub…", expanded=True) as status:
            try:
                report = sync_github(store(), token=token, repo=repo, limit=int(limit),
                                     progress=lambda r: status.write(f"run {r.workflow_run_id}: {r.status}"))
                flash("warning" if report.stopped or report.count("error") else "success", report.describe())
            except MissingTokenError as exc:
                flash("error", str(exc))
            except GitHubError as exc:
                flash("error", f"GitHub sync failed: {exc}")
        refresh()
    if not token:
        sb.caption("GitHub sync/trigger disabled: set `GITHUB_TOKEN` (env or `.streamlit/secrets.toml`). "
                   "Sync needs `actions: read`; triggering a run needs `actions: write`.")
    else:
        sb.caption(f"Repository: `{repo}`")

    sb.divider()
    sb.caption(f"History: {len(runs)} run(s) in `{store().db_path}`")
    sb.caption("GitHub artifacts expire after 30 days; this SQLite history and the copied "
               "screenshots/reports are the long-term record.")
    if sb.button("Reload data", icon=":material/refresh:", width="stretch"):
        refresh()
    return {"base_url": base_url.strip() or "http://localhost:3000", "branch": branch.strip() or "main",
            "token": token, "repo": repo}


# -------------------------------------------------------------- run triggers
def run_panel(settings: dict) -> None:
    running = st.session_state.get("run_requested", False)
    with st.container(border=True):
        c = st.columns([3, 3, 2])
        with c[0]:
            st.markdown("**Run all tests locally**")
            st.caption(f"pytest + headless Chrome against `{settings['base_url']}`")
            if st.button("Run all tests", type="primary", icon=":material/play_arrow:", disabled=running,
                         key="run_local", width="stretch"):
                st.session_state["run_requested"] = True
                st.rerun()
        with c[1]:
            st.markdown("**Trigger CI run on GitHub**")
            st.caption(f"`{WORKFLOW_FILE}` on branch `{settings['branch']}`")
            if st.button("Trigger CI run", icon=":material/rocket_launch:", key="run_ci", width="stretch",
                         disabled=not settings["token"] or running,
                         help=None if settings["token"] else "Needs GITHUB_TOKEN with actions:write"):
                ok, msg = runner.dispatch_workflow(settings["token"], settings["repo"], settings["branch"])
                if ok:
                    flash("success", f"{msg} When it finishes, press **Sync from GitHub** in the sidebar.")
                else:
                    flash("error", f"Could not trigger the workflow: {msg}")
                st.rerun()
            if not settings["token"]:
                st.caption("Disabled: set `GITHUB_TOKEN` (needs `actions: write`).")
        with c[2]:
            st.markdown("**GitHub Actions**")
            st.link_button("Open Actions", f"https://github.com/{settings['repo']}/actions/workflows/{WORKFLOW_FILE}",
                           icon=":material/open_in_new:", width="stretch")

        if running:
            try:
                execute_local_run(settings["base_url"])
            finally:
                st.session_state["run_requested"] = False
            refresh()

        log = st.session_state.get("last_log")
        if log and not running:
            with st.expander("Output of the last local run"):
                st.code(log, language="text")


def execute_local_run(base_url: str) -> None:
    up, detail = runner.app_is_up(base_url)
    if not up:
        flash("error", f"App is not reachable ({detail}). Start the app first: `{runner.START_APP_HINT}`")
        return
    if runner.test_python() is None:
        flash("error", f"`testing/.venv` not found. Create it with: `{runner.SETUP_HINT}`")
        return

    lines: list[str] = []
    code = None
    with st.status("Running all tests…", expanded=True) as status:
        box = st.empty()
        last = 0.0
        for item in runner.run_pytest(base_url):
            if isinstance(item, int):
                code = item
                break
            lines.append(item)
            if time.monotonic() - last > 0.3:
                box.code("\n".join(lines[-40:]), language="text")
                last = time.monotonic()
        box.code("\n".join(lines[-40:]), language="text")
        status.update(label=f"pytest finished (exit code {code})",
                      state="complete" if code == 0 else "error", expanded=False)
    st.session_state["last_log"] = "\n".join(lines[-400:])

    try:
        result = ingest_reports_dir(store(), reports_dir_from_env())
    except IngestError as exc:
        flash("error", f"pytest exited with code {code}, but results could not be ingested: {exc}")
        return
    failing = result.failed + result.error
    if failing:
        st.session_state["toast"] = (f"Run FAILED: {failing} of {result.total} tests failed", ":material/cancel:")
    else:
        st.session_state["toast"] = (f"Run PASSED: {result.passed}/{result.total} tests passed",
                                     ":material/check_circle:")
    flash("success" if not failing else "warning", result.describe())


# ------------------------------------------------------------ command center
def header(latest: dict | None) -> None:
    if latest is None:
        pill, meta = '<span class="bt-pill" style="background:#9a9890">NO RUNS</span>', "No runs ingested yet"
    else:
        status = an.run_status(latest)
        color = {"PASSED": TONES["good"], "FAILED": TONES["bad"]}.get(status, "#9a9890")
        pill = f'<span class="bt-pill" style="background:{color}">{status}</span>'
        sha = (latest.get("commit_sha") or "")[:7] or "—"
        meta = (f"Last run <b>{an.time_ago(latest['started_at'])}</b> · {an.fmt_ts(latest['started_at'])} · "
                f"branch <code>{html.escape(latest.get('branch') or '—')}</code> · "
                f"commit <code>{html.escape(sha)}</code> · trigger {html.escape(latest.get('trigger') or '—')}")
    st.markdown(f'<div class="bt-header"><div class="bt-title">BankTest — <span>QA Command Center</span></div>'
                f'{pill}</div><div class="bt-meta">{meta}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, tone: str = "neutral", sub: str = "", delta: float | None = None,
        unit: str = "", higher_is_better: bool | None = None) -> str:
    delta_html = ""
    if delta is not None:
        if abs(delta) < 1e-9:
            delta_html = '<span class="d-flat">no change</span>'
        else:
            cls = "d-flat" if higher_is_better is None else (
                "d-good" if (delta > 0) == higher_is_better else "d-bad")
            arrow = "▲" if delta > 0 else "▼"
            delta_html = f'<span class="{cls}">{arrow} {abs(delta):g}{unit}</span> vs prev'
    sub_html = " · ".join(x for x in (delta_html, html.escape(sub)) if x)
    return (f'<div class="kpi" style="--tone:{TONES[tone]}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub_html or "&nbsp;"}</div></div>')


def avg_duration(results: pd.DataFrame) -> float | None:
    d = results.loc[results["outcome"] != "skipped", "duration_seconds"].dropna()
    return float(d.mean()) if len(d) else None


def command_center(runs: pd.DataFrame, cases: list[dict], all_results: pd.DataFrame) -> None:
    if runs.empty:
        st.info(EMPTY_STATE, icon=":material/info:")
        if cases:
            blocked = sum(1 for c in cases if (c.get("status") or "").lower() == "blocked")
            st.caption(f"Catalogue: {len(cases)} test cases, {blocked} blocked. "
                       "Press **Run all tests** above to create the first run.")
        return

    latest = an.row_dict(runs.iloc[0])
    prev = an.row_dict(runs.iloc[1]) if len(runs) > 1 else None
    results = all_results[all_results["run_id"] == latest["run_id"]]
    prev_results = all_results[all_results["run_id"] == prev["run_id"]] if prev else None

    failing_n = latest["failed"] + latest["error"]
    rate = latest["pass_rate"]
    avg = avg_duration(results)
    prev_avg = avg_duration(prev_results) if prev_results is not None else None
    blocked = sum(1 for c in cases if (c.get("status") or "").lower() == "blocked")

    def d(key):
        return None if prev is None else latest[key] - prev[key]

    cards = [
        kpi("Total cases", str(latest["total"]), sub=f"{len(cases)} in catalogue · {blocked} blocked"
            if cases else "catalogue not found", delta=d("total")),
        kpi("Pass rate", f"{rate:.1f}%", "good" if rate >= 95 else "warn" if rate >= 80 else "bad",
            delta=None if prev is None else round(rate - prev["pass_rate"], 2), unit=" pp", higher_is_better=True),
        kpi("Failed", str(failing_n), "bad" if failing_n else "good",
            sub=f"{latest['failed']} failed · {latest['error']} error · {latest['skipped']} skipped",
            delta=None if prev is None else failing_n - (prev["failed"] + prev["error"]), higher_is_better=False),
        kpi("Critical failures", str(latest["critical_failed"]), "bad" if latest["critical_failed"] else "good",
            delta=d("critical_failed"), higher_is_better=False),
        kpi("Avg test duration", an.fmt_duration(avg), sub=f"run {an.fmt_duration(latest['duration_seconds'])}",
            delta=None if avg is None or prev_avg is None else round(avg - prev_avg, 2), unit="s",
            higher_is_better=False),
        kpi("Last run", an.time_ago(latest["started_at"]), sub=f"{len(runs)} runs in history"),
    ]
    for col, card in zip(st.columns(6), cards):
        col.markdown(card, unsafe_allow_html=True)

    crit = by_priority(results[results["outcome"].isin(an.FAILING)
                               & (results["priority"].fillna("").str.lower() == "critical")])
    if latest["critical_failed"]:
        ids = ", ".join(sorted(set(crit["tc_id"].dropna()))) or f"{latest['critical_failed']} test(s)"
        st.markdown(f'<div class="gate gate-fail"><b>⛔ QUALITY GATE FAILED</b> — critical test failures: '
                    f'<b>{html.escape(ids)}</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="gate gate-pass"><b>✅ QUALITY GATE PASSED</b> — no critical test failures '
                    'in the latest run</div>', unsafe_allow_html=True)

    c = st.columns([1, 1.2, 1.5])
    with c[0]:
        st.markdown("**Latest run outcomes**")
        st.plotly_chart(charts.outcome_donut(latest), width="stretch", config=CHART_CONFIG, key="chart1")
    with c[1]:
        st.markdown("**Failures by module (latest run)**")
        by_module = an.failures_by_module(results)
        if by_module.empty:
            st.success("No failures in the latest run.", icon=":material/check_circle:")
        else:
            st.plotly_chart(charts.module_failures(by_module), width="stretch", config=CHART_CONFIG, key="chart2")
    with c[2]:
        st.markdown("**Pass rate trend**")
        st.plotly_chart(charts.pass_rate_trend(an.runs_chronological(runs).tail(30)), width="stretch",
                        config=CHART_CONFIG, key="chart3")

    needs_attention(latest, results)

    st.markdown("#### Recent runs")
    recent = runs.head(15).copy()
    recent["status"] = recent.apply(an.run_status, axis=1).map({"PASSED": "🟢 PASSED", "FAILED": "🔴 FAILED"}) \
        .fillna("⚪ NO TESTS")
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


def needs_attention(latest: dict, results: pd.DataFrame) -> None:
    failing = by_priority(results[results["outcome"].isin(an.FAILING)], "seq")
    st.markdown(f"#### Needs attention ({len(failing)})")
    if failing.empty:
        st.success("Nothing failing in the latest run.", icon=":material/check_circle:")
        return
    for _, row in failing.iterrows():
        t = an.row_dict(row)
        with st.container(border=True):
            left, right = st.columns([5, 2])
            outcome = f'<span class="chip o-{t["outcome"]}">{t["outcome"].upper()}</span>'
            left.markdown(
                f'{priority_chip(t["priority"])}{outcome}<b>{html.escape(t["tc_id"] or t["nodeid"] or "?")}</b> · '
                f'{html.escape(t["title"] or "")} <span style="color:#6b6880">— {html.escape(t["module"] or "")}'
                f'</span>', unsafe_allow_html=True)
            left.caption((t["message"] or "No failure message recorded.")[:300])
            if t["traceback"]:
                with left.expander("Traceback"):
                    st.code(t["traceback"], language="python")
            shot = store().artifact_path(latest["run_id"], t["screenshot"])
            if shot:
                with right.expander("Screenshot", expanded=True):
                    st.image(str(shot), width="stretch")
            else:
                right.caption("No screenshot")


# ----------------------------------------------------------- test management
def test_management(cases: list[dict], catalogue_error: str | None, all_results: pd.DataFrame) -> None:
    if catalogue_error:
        st.error(f"Could not read the test-case catalogue: {catalogue_error}")
    if not cases:
        st.info(f"No test-case catalogue found at `{catalogue_path_from_env()}`. "
                "The test suite owner maintains it (APP_CONTRACT.md §5).", icon=":material/info:")
        return

    table = by_priority(an.catalogue_table(cases, all_results), "module", "tc_id").reset_index(drop=True)
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

    display = view.assign(last_run=view["last_run_at"].map(an.fmt_ts),
                          current_status=view["current_status"].map(lambda s: STATUS_CHIPS.get(s, s)))
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
    view = by_priority(results, "seq")  # failing first, then by priority
    view = pd.concat([view[view["outcome"].isin(an.FAILING)], view[~view["outcome"].isin(an.FAILING)]])
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
        st.plotly_chart(charts.run_test_durations(view), width="stretch", config=CHART_CONFIG, key="chart4")

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
        st.plotly_chart(charts.outcome_trend(chrono), width="stretch", config=CHART_CONFIG, key="chart5")
    with c[1]:
        st.markdown("**Pass rate per run**")
        st.plotly_chart(charts.pass_rate_trend(chrono), width="stretch", config=CHART_CONFIG, key="chart6")

    c = st.columns(2)
    with c[0]:
        st.markdown("**Failing results by module**")
        by_module = an.failures_by_module(results)
        if by_module.empty:
            st.success("No failures in the selected runs.", icon=":material/check_circle:")
        else:
            st.plotly_chart(charts.module_failures(by_module), width="stretch", config=CHART_CONFIG, key="chart7")
    with c[1]:
        st.markdown("**Run duration**")
        st.plotly_chart(charts.duration_trend(chrono), width="stretch", config=CHART_CONFIG, key="chart8")

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
    st.markdown(CSS, unsafe_allow_html=True)
    db = str(store().db_path)
    runs = load_runs(db)
    cases, catalogue_error = load_cases(str(catalogue_path_from_env()))
    all_results = load_results(db) if not runs.empty else store().get_results().iloc[0:0]
    settings = sidebar(runs)

    header(an.row_dict(runs.iloc[0]) if not runs.empty else None)
    toast = st.session_state.pop("toast", None)
    if toast:
        st.toast(toast[0], icon=toast[1])
    message = st.session_state.pop("flash", None)
    if message:
        getattr(st, message[0])(message[1])
    run_panel(settings)

    tabs = st.tabs(["Dashboard", "Test Management", "Execution Details", "History & Analytics"])
    with tabs[0]:
        command_center(runs, cases, all_results)
    with tabs[1]:
        test_management(cases, catalogue_error, all_results)
    with tabs[2]:
        execution_details(runs)
    with tabs[3]:
        history(runs, all_results)


main()
