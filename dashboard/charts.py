"""Plotly figure builders. Status colours are reserved for outcomes only."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

OUTCOME_COLORS = {
    "passed": "#0ca30c",   # status good
    "failed": "#d03b3b",   # status critical
    "error": "#ec835a",    # status serious
    "skipped": "#9a9890",  # neutral
    "unknown": "#c3c2b7",
}
ACCENT = "#7f22fe"          # app primary, used for single-series non-status charts
GRID = "#e9e8e4"
TEXT_MUTED = "#52514e"


def _layout(fig: go.Figure, height: int = 320, **kwargs) -> go.Figure:
    layout = dict(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color=TEXT_MUTED),
        hoverlabel=dict(bgcolor="white", font_size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
    )
    layout.update(kwargs)
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def outcome_trend(runs: pd.DataFrame) -> go.Figure:
    """Stacked outcome counts per run (runs in chronological order)."""
    fig = go.Figure()
    custom = runs[["run_id", "branch", "commit_sha", "pass_rate"]].fillna("—").astype(str).values
    for outcome in ("passed", "failed", "error", "skipped"):
        fig.add_bar(
            x=runs["label"], y=runs[outcome], name=outcome.capitalize(),
            marker=dict(color=OUTCOME_COLORS[outcome], line=dict(color="white", width=1)),
            customdata=custom,
            hovertemplate=(f"<b>%{{x}}</b><br>{outcome.capitalize()}: %{{y}}<br>"
                           "Pass rate: %{customdata[3]}%<br>Branch: %{customdata[1]}<br>"
                           "Commit: %{customdata[2]}<br>Run: %{customdata[0]}<extra></extra>"),
        )
    fig.update_layout(barmode="stack", bargap=0.35)
    fig.update_xaxes(type="category")
    fig.update_yaxes(title="Tests", rangemode="tozero")
    return _layout(fig)


def pass_rate_trend(runs: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=runs["label"], y=runs["pass_rate"], mode="lines+markers", name="Pass rate",
        line=dict(color=ACCENT, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
        customdata=runs[["run_id", "commit_sha"]].fillna("—").astype(str).values,
        hovertemplate="<b>%{x}</b><br>Pass rate: %{y:.2f}%<br>Commit: %{customdata[1]}<extra></extra>",
    ))
    fig.update_xaxes(type="category")
    fig.update_yaxes(title="Pass rate (%)", range=[0, 105], ticksuffix="%")
    return _layout(fig, showlegend=False, hovermode="x")


def duration_trend(runs: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=runs["label"], y=runs["duration_seconds"], mode="lines+markers", name="Run duration",
        line=dict(color=ACCENT, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
        customdata=runs[["run_id", "total"]].astype(str).values,
        hovertemplate="<b>%{x}</b><br>Duration: %{y:.1f}s<br>Tests: %{customdata[1]}<extra></extra>",
    ))
    fig.update_xaxes(type="category")
    fig.update_yaxes(title="Seconds", rangemode="tozero")
    return _layout(fig, showlegend=False, hovermode="x")


def module_failures(df: pd.DataFrame) -> go.Figure:
    """Horizontal stacked bars: failed vs error results per module."""
    df = df.sort_values("total")
    fig = go.Figure()
    for outcome in ("failed", "error"):
        fig.add_bar(
            y=df["module"], x=df[outcome], name=outcome.capitalize(), orientation="h",
            marker=dict(color=OUTCOME_COLORS[outcome], line=dict(color="white", width=1)),
            hovertemplate=f"<b>%{{y}}</b><br>{outcome.capitalize()}: %{{x}}<extra></extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.35)
    fig.update_xaxes(title="Failing results", rangemode="tozero", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return _layout(fig, height=max(220, 60 + 36 * len(df)))


def run_test_durations(results: pd.DataFrame) -> go.Figure:
    """Per-test duration bars for one run, coloured by outcome."""
    df = results.copy()
    df["name"] = df["tc_id"].fillna(df["nodeid"]).fillna("?")
    dup = df["name"].duplicated(keep=False)  # parametrised tests share a tc_id
    df.loc[dup, "name"] = df.loc[dup, "name"] + " · " + df.loc[dup, "nodeid"].fillna("").str.split("::").str[-1]
    df = df.sort_values("duration_seconds", ascending=True)
    fig = go.Figure()
    for outcome, grp in df.groupby("outcome", sort=False):
        fig.add_bar(
            y=grp["name"], x=grp["duration_seconds"], orientation="h", name=str(outcome).capitalize(),
            marker=dict(color=OUTCOME_COLORS.get(outcome, OUTCOME_COLORS["unknown"])),
            customdata=grp[["title"]].fillna("").values,
            hovertemplate="<b>%{y}</b> %{customdata[0]}<br>%{x:.2f}s<extra></extra>",
        )
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=list(df["name"]), showgrid=False)
    fig.update_xaxes(title="Seconds", showgrid=True, gridcolor=GRID, rangemode="tozero")
    return _layout(fig, height=max(240, 60 + 22 * len(df)), bargap=0.3)


def outcome_donut(run: dict) -> go.Figure:
    """Outcome split of one run, pass rate in the centre."""
    outcomes = [o for o in ("passed", "failed", "error", "skipped") if run.get(o)]
    fig = go.Figure(go.Pie(
        labels=[o.capitalize() for o in outcomes], values=[run[o] for o in outcomes], hole=0.64, sort=False,
        marker=dict(colors=[OUTCOME_COLORS[o] for o in outcomes], line=dict(color="white", width=2)),
        textinfo="value", textfont=dict(color="white", size=13),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{run.get('pass_rate', 0):.1f}%</b><br><span style='font-size:11px'>pass rate</span>",
                       showarrow=False, font=dict(size=20, color="#1f1d2b"))
    return _layout(fig, height=280, legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"))
