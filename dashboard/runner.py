"""Trigger test runs from the dashboard: local pytest or a GitHub workflow_dispatch."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterator

import requests

from ingest import GITHUB_API, WORKFLOW_FILE

TESTING_DIR = Path(__file__).resolve().parent.parent / "testing"
TEST_PYTHON = TESTING_DIR / ".venv" / "bin" / "python"
SETUP_HINT = (
    "cd testing && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
)
START_APP_HINT = "npm run build && npm start"


def app_is_up(base_url: str, timeout: float = 5) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/bank/login"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return False, f"{url} unreachable ({exc.__class__.__name__})"
    if resp.status_code >= 400:
        return False, f"{url} returned HTTP {resp.status_code}"
    return True, f"{url} is up"


def test_python() -> Path | None:
    return TEST_PYTHON if TEST_PYTHON.exists() else None


def run_pytest(base_url: str) -> Iterator[str | int]:
    """Run the suite, yielding output lines; the final item is the exit code (int).

    The process is terminated if the consumer stops iterating early
    (e.g. a Streamlit rerun interrupts the script).
    """
    python = test_python()
    if python is None:
        raise FileNotFoundError(f"{TEST_PYTHON} not found. Create it with: {SETUP_HINT}")
    env = {**os.environ, "BASE_URL": base_url.rstrip("/"), "HEADLESS": "1", "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [str(python), "-m", "pytest", "--color=no"],
        cwd=TESTING_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
        yield proc.wait()
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def dispatch_workflow(token: str, repo: str, ref: str = "main",
                      workflow: str = WORKFLOW_FILE) -> tuple[bool, str]:
    """POST a workflow_dispatch event. Needs a token with actions:write."""
    url = f"{GITHUB_API}/repos/{repo}/actions/workflows/{workflow}/dispatches"
    try:
        resp = requests.post(url, json={"ref": ref}, timeout=30, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "banktest-dashboard",
        })
    except requests.RequestException as exc:
        return False, f"network error: {exc}"
    if resp.status_code == 204:
        return True, f"Workflow dispatched on `{ref}`."
    detail = ""
    try:
        detail = resp.json().get("message", "")
    except ValueError:
        pass
    hints = {401: "token rejected", 403: "token needs actions:write",
             404: "repo/workflow not found or token lacks access",
             422: "branch not found or workflow has no workflow_dispatch trigger"}
    return False, f"HTTP {resp.status_code}: {hints.get(resp.status_code, '')} {detail}".strip()
