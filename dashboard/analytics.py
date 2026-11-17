"""Pure pandas computations behind the dashboard views (no Streamlit here)."""

from __future__ import annotations

import pandas as pd

FAILING = ("failed", "error")
# Worst outcome wins when several results share a tc_id within one run.
_SEVERITY = {"error": 4, "failed": 3, "unknown": 2, "passed": 1, "skipped": 0}


def row_dict(row: pd.Series) -> dict:
    """Series -> dict with pandas NaN/NaT turned into None."""
    return {k: (None if not isinstance(v, (list, dict)) and pd.isna(v) else v) for k, v in row.items()}


def fmt_duration(seconds) -> str:
    if seconds is None or pd.isna(seconds):
        return "—"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def fmt_ts(value) -> str:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    return "—" if pd.isna(ts) else ts.strftime("%Y-%m-%d %H:%M UTC")


def time_ago(value, now=None) -> str:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return "—"
    now = now or pd.Timestamp.now(tz="UTC")
    secs = max((now - ts).total_seconds(), 0)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{int(secs // size)}{unit} ago"
    return "just now"


PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def priority_rank(value) -> int:
    return PRIORITY_RANK.get(str(value).lower(), 9)


def run_status(run) -> str:
    """PASSED / FAILED / NO TESTS for a runs row (dict or Series)."""
    if not run["total"]:
        return "NO TESTS"
    return "FAILED" if (run["failed"] or 0) + (run["error"] or 0) > 0 else "PASSED"


def runs_chronological(runs: pd.DataFrame) -> pd.DataFrame:
    """Runs oldest -> newest with a unique, readable axis label per run."""
    if runs.empty:
        return runs.assign(label=pd.Series(dtype=str), started=pd.Series(dtype="datetime64[ns, UTC]"))
    df = runs.copy()
    df["started"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["ingested"] = pd.to_datetime(df["ingested_at"], utc=True, errors="coerce")
    df["sort_key"] = df["started"].fillna(df["ingested"])
    df = df.sort_values(["sort_key", "ingested"]).reset_index(drop=True)
    df["label"] = [
        f"#{i + 1} {key:%m-%d %H:%M}" if pd.notna(key) else f"#{i + 1}"
        for i, key in enumerate(df["sort_key"])
    ]
    df["status"] = df.apply(run_status, axis=1)
    return df


def per_case_outcomes(results: pd.DataFrame) -> pd.DataFrame:
    """One row per (run, tc_id) with the worst outcome among its test results."""
    cols = ["run_id", "tc_id", "title", "module", "priority", "outcome",
            "message", "run_started_at", "run_commit_sha", "duration_seconds"]
    if results.empty:
        return pd.DataFrame(columns=cols)
    df = results.copy()
    df["tc_id"] = df["tc_id"].fillna(df["nodeid"]).fillna("(unidentified)")
    df["severity"] = df["outcome"].map(_SEVERITY).fillna(2)
    df = df.sort_values(["run_id", "tc_id", "severity"], ascending=[True, True, False])
    agg = df.groupby(["run_id", "tc_id"], as_index=False, sort=False).agg(
        title=("title", "first"), module=("module", "first"), priority=("priority", "first"),
        outcome=("outcome", "first"), message=("message", "first"),
        run_started_at=("run_started_at", "first"), run_commit_sha=("run_commit_sha", "first"),
        duration_seconds=("duration_seconds", "sum"),
    )
    return agg[cols]


def latest_status_by_case(results: pd.DataFrame) -> pd.DataFrame:
    """Latest outcome of each tc_id across all runs."""
    cases = per_case_outcomes(results)
    if cases.empty:
        return pd.DataFrame(columns=["tc_id", "latest_outcome", "last_run_id", "last_run_at", "last_message"])
    cases["ts"] = pd.to_datetime(cases["run_started_at"], utc=True, errors="coerce")
    latest = cases.sort_values("ts").groupby("tc_id", as_index=False).last()
    return latest.rename(columns={
        "outcome": "latest_outcome", "run_id": "last_run_id",
        "run_started_at": "last_run_at", "message": "last_message",
    })[["tc_id", "latest_outcome", "last_run_id", "last_run_at", "last_message"]]


def current_status(case: dict, latest_outcome) -> str:
    status = (case.get("status") or "").strip().lower()
    if status == "blocked":
        return "Blocked"
    if status in ("not applicable", "n/a", "na"):
        return "Not applicable"
    if isinstance(latest_outcome, str) and latest_outcome:
        return latest_outcome.capitalize()
    return "Not run" if case.get("automated") else "Manual"


def catalogue_table(cases: list[dict], results: pd.DataFrame) -> pd.DataFrame:
    """Catalogue joined with each case's latest automated result."""
    if not cases:
        return pd.DataFrame()
    df = pd.DataFrame(cases)
    latest = latest_status_by_case(results)
    df = df.merge(latest, on="tc_id", how="left")
    df["current_status"] = [
        current_status(case, outcome)
        for case, outcome in zip(cases, df["latest_outcome"].tolist())
    ]
    return df


def failure_stats(results: pd.DataFrame) -> pd.DataFrame:
    """Per test case: executions, failures, failure rate and flakiness."""
    cases = per_case_outcomes(results)
    cases = cases[cases["outcome"] != "skipped"]
    if cases.empty:
        return pd.DataFrame(columns=["tc_id", "title", "module", "priority", "runs", "failures",
                                     "failure_rate", "flips", "pattern", "last_failure_at", "last_message"])
    cases = cases.assign(
        failing=cases["outcome"].isin(FAILING),
        ts=pd.to_datetime(cases["run_started_at"], utc=True, errors="coerce"),
    ).sort_values("ts")
    rows = []
    for tc_id, grp in cases.groupby("tc_id", sort=False):
        failures = int(grp["failing"].sum())
        if failures == 0:
            continue
        fails = grp[grp["failing"]]
        runs = len(grp)
        # Outcome changes between consecutive runs (pass<->fail) = instability.
        flips = int((grp["failing"].astype(int).diff().abs() == 1).sum())
        # Flaky = both passed and failed on the same commit (code unchanged).
        by_commit = grp.dropna(subset=["run_commit_sha"]).groupby("run_commit_sha")["failing"].nunique()
        if failures == runs:
            pattern = "Always failing"
        elif (by_commit > 1).any():
            pattern = "Flaky"
        elif grp["failing"].iloc[-1]:
            pattern = "Failing now"
        else:
            pattern = "Recovered"
        rows.append({
            "tc_id": tc_id, "title": grp["title"].iloc[-1], "module": grp["module"].iloc[-1],
            "priority": grp["priority"].iloc[-1], "runs": runs, "failures": failures,
            "failure_rate": round(failures / runs * 100, 1), "flips": flips, "pattern": pattern,
            "last_failure_at": fails["run_started_at"].iloc[-1],
            "last_message": fails["message"].iloc[-1],
        })
    if not rows:  # tests ran but none ever failed
        return pd.DataFrame(columns=["tc_id", "title", "module", "priority", "runs", "failures",
                                     "failure_rate", "flips", "pattern", "last_failure_at", "last_message"])
    out = pd.DataFrame(rows)
    return out.sort_values(["failures", "failure_rate"], ascending=False).reset_index(drop=True)


def failures_by_module(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(columns=["module", "failed", "error", "total"])
    df = results[results["outcome"].isin(FAILING)].copy()
    if df.empty:
        return pd.DataFrame(columns=["module", "failed", "error", "total"])
    df["module"] = df["module"].fillna("Unassigned")
    out = (df.pivot_table(index="module", columns="outcome", values="seq", aggfunc="count", fill_value=0)
             .reindex(columns=list(FAILING), fill_value=0).reset_index())
    out.columns.name = None
    out["total"] = out["failed"] + out["error"]
    return out.sort_values("total", ascending=False).reset_index(drop=True)


def slowest_tests(results: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(columns=["tc_id", "title", "runs", "avg_seconds", "max_seconds"])
    df = results[results["outcome"] != "skipped"].dropna(subset=["duration_seconds"]).copy()
    df["tc_id"] = df["tc_id"].fillna(df["nodeid"])
    out = df.groupby("tc_id", as_index=False).agg(
        title=("title", "last"), runs=("run_id", "nunique"),
        avg_seconds=("duration_seconds", "mean"), max_seconds=("duration_seconds", "max"),
    )
    out["avg_seconds"] = out["avg_seconds"].round(2)
    return out.sort_values("avg_seconds", ascending=False).head(top).reset_index(drop=True)
