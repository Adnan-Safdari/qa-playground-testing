"""SQLite-backed execution history for the BankTest dashboard.

GitHub Actions artifacts expire (30 days), so every ingested run is normalised
into SQLite and its evidence files (report.html, junit.xml, results.json,
screenshots) are copied to ``<artifacts_dir>/<run_id>/``. This store is the
long-term history the dashboard reads from.

Paths:
    BANKTEST_DB_PATH        SQLite file (default: dashboard/data/history.db)
    BANKTEST_ARTIFACTS_DIR  evidence files (default: <db dir>/artifacts)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DASHBOARD_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = DASHBOARD_DIR / "data" / "history.db"

# Report files copied (when present) next to a run's screenshots.
REPORT_FILES = ("report.html", "junit.xml", "results.json")

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    source            TEXT NOT NULL,           -- local | github
    started_at        TEXT,                    -- ISO-8601 UTC
    finished_at       TEXT,
    duration_seconds  REAL,
    commit_sha        TEXT,
    branch            TEXT,
    workflow_run_id   TEXT,
    workflow_run_url  TEXT,
    trigger           TEXT,
    base_url          TEXT,
    browser           TEXT,
    headless          INTEGER,
    total             INTEGER NOT NULL DEFAULT 0,
    passed            INTEGER NOT NULL DEFAULT 0,
    failed            INTEGER NOT NULL DEFAULT 0,
    skipped           INTEGER NOT NULL DEFAULT 0,
    error             INTEGER NOT NULL DEFAULT 0,
    pass_rate         REAL NOT NULL DEFAULT 0,
    critical_failed   INTEGER NOT NULL DEFAULT 0,
    schema_version    INTEGER,
    ingested_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    seq               INTEGER NOT NULL,        -- order within the run
    tc_id             TEXT,
    title             TEXT,
    module            TEXT,
    priority          TEXT,
    nodeid            TEXT,
    outcome           TEXT NOT NULL,
    duration_seconds  REAL,
    message           TEXT,
    traceback         TEXT,
    screenshot        TEXT,                    -- path relative to the run's artifact dir
    failure_context   TEXT                     -- JSON: url, page_title, console_errors, captured_at
);

CREATE INDEX IF NOT EXISTS idx_results_run ON test_results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_tc ON test_results(tc_id);
CREATE INDEX IF NOT EXISTS idx_runs_wf ON runs(workflow_run_id);
"""

_RUN_COLUMNS = (
    "run_id", "source", "started_at", "finished_at", "duration_seconds",
    "commit_sha", "branch", "workflow_run_id", "workflow_run_url", "trigger",
    "base_url", "browser", "headless", "total", "passed", "failed", "skipped",
    "error", "pass_rate", "critical_failed", "schema_version", "ingested_at",
)
_TEST_COLUMNS = (
    "run_id", "seq", "tc_id", "title", "module", "priority", "nodeid", "outcome",
    "duration_seconds", "message", "traceback", "screenshot", "failure_context",
)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def default_db_path() -> Path:
    env = os.environ.get("BANKTEST_DB_PATH")
    return Path(env).expanduser() if env else DEFAULT_DB_PATH


def default_artifacts_dir(db_path: Path) -> Path:
    env = os.environ.get("BANKTEST_ARTIFACTS_DIR")
    return Path(env).expanduser() if env else Path(db_path).parent / "artifacts"


def safe_dirname(run_id: str) -> str:
    """Filesystem-safe directory name for a run id."""
    name = _SAFE_NAME.sub("_", str(run_id)).strip("._")
    return name or "run"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class HistoryStore:
    def __init__(self, db_path: Path | str | None = None, artifacts_dir: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else default_artifacts_dir(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------ infra
    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(test_results)")}
            if "failure_context" not in cols:  # DBs created before bug reports existed
                conn.execute("ALTER TABLE test_results ADD COLUMN failure_context TEXT")
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def run_dir(self, run_id: str) -> Path:
        return self.artifacts_dir / safe_dirname(run_id)

    # ----------------------------------------------------------------- writes
    def store_artifacts(self, run_id: str, reports_dir: Path, tests: list[dict]) -> list[dict]:
        """Copy report files and referenced screenshots into the run's artifact dir.

        Returns ``tests`` with ``screenshot`` rewritten to a path relative to the
        run dir, or None when the file is missing or points outside reports_dir.
        """
        reports_dir = Path(reports_dir)
        dest = self.run_dir(run_id)
        if dest.exists() and dest.resolve() == reports_dir.resolve():
            raise ValueError("reports_dir is the run's own artifact directory; refusing to overwrite it")
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        for name in REPORT_FILES:
            src = reports_dir / name
            if src.is_file():
                shutil.copy2(src, dest / name)

        updated = []
        for test in tests:
            test = dict(test)
            rel = test.get("screenshot")
            test["screenshot"] = None
            if rel:
                src = reports_dir / rel
                if src.is_file() and _is_within(src, reports_dir):
                    rel_clean = src.resolve().relative_to(reports_dir.resolve())
                    target = dest / rel_clean
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
                    test["screenshot"] = rel_clean.as_posix()
            updated.append(test)
        return updated

    def save_run(self, run: dict, tests: list[dict], source: str) -> bool:
        """Insert or replace a run and its results atomically.

        Returns True if the run already existed (and was replaced).
        """
        row = {col: run.get(col) for col in _RUN_COLUMNS}
        row["source"] = source
        row["ingested_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if row["headless"] is not None:
            row["headless"] = int(bool(row["headless"]))
        with self._connect() as conn:
            existed = conn.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (row["run_id"],)
            ).fetchone() is not None
            conn.execute("DELETE FROM runs WHERE run_id = ?", (row["run_id"],))
            conn.execute(
                f"INSERT INTO runs ({', '.join(_RUN_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _RUN_COLUMNS)})",
                [row[c] for c in _RUN_COLUMNS],
            )
            conn.executemany(
                f"INSERT INTO test_results ({', '.join(_TEST_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _TEST_COLUMNS)})",
                [
                    [row["run_id"], i] + [
                        json.dumps(t[c]) if c == "failure_context" and isinstance(t.get(c), dict) else t.get(c)
                        for c in _TEST_COLUMNS[2:]
                    ]
                    for i, t in enumerate(tests)
                ],
            )
        return existed

    def delete_run(self, run_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        shutil.rmtree(self.run_dir(run_id), ignore_errors=True)

    def prune(self, keep_last: int) -> list[str]:
        """Retention: keep only the newest ``keep_last`` runs. Returns deleted ids."""
        runs = self.list_runs()
        doomed = list(runs["run_id"].iloc[max(keep_last, 0):]) if not runs.empty else []
        for run_id in doomed:
            self.delete_run(run_id)
        return doomed

    # ------------------------------------------------------------------ reads
    def run_exists(self, run_id: str) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT 1 FROM runs WHERE run_id = ?", (str(run_id),)).fetchone() is not None

    def workflow_run_ingested(self, workflow_run_id) -> bool:
        wid = str(workflow_run_id)
        with self._connect() as conn:
            return conn.execute(
                "SELECT 1 FROM runs WHERE workflow_run_id = ? OR run_id = ?", (wid, wid)
            ).fetchone() is not None

    def list_runs(self) -> pd.DataFrame:
        """All runs, newest first."""
        with self._connect() as conn:
            return pd.read_sql_query(
                "SELECT * FROM runs ORDER BY COALESCE(started_at, ingested_at) DESC, ingested_at DESC",
                conn,
            )

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def get_results(self, run_id: str | None = None) -> pd.DataFrame:
        """Test results (optionally for one run), joined with run start time."""
        sql = (
            "SELECT t.*, r.started_at AS run_started_at, r.branch AS run_branch, "
            "r.commit_sha AS run_commit_sha "
            "FROM test_results t JOIN runs r ON r.run_id = t.run_id"
        )
        params: tuple = ()
        if run_id is not None:
            sql += " WHERE t.run_id = ?"
            params = (run_id,)
        sql += " ORDER BY COALESCE(r.started_at, r.ingested_at), t.seq"
        with self._connect() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def artifact_path(self, run_id: str, relpath: str | None) -> Path | None:
        """Absolute path of a stored artifact file, or None if absent/unsafe."""
        if not isinstance(relpath, str) or not relpath:
            return None
        root = self.run_dir(run_id)
        path = root / relpath
        if path.is_file() and _is_within(path, root):
            return path
        return None
