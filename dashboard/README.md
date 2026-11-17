# BankTest Dashboard

A Streamlit dashboard for the BankTest Selenium/Pytest results. It shows only real
execution data: runs ingested from `testing/reports/results.json` and the
test-case catalogue in `testing/test_cases.json` (see `testing/APP_CONTRACT.md` §4–5).

## Run

```bash
python3 -m venv dashboard/.venv
dashboard/.venv/bin/pip install -r dashboard/requirements.txt
dashboard/.venv/bin/streamlit run dashboard/app.py
```

Tabs: **Overview** (latest run status, counts, pass rate, durations, quality gate, recent runs) ·
**Test Management** (filterable catalogue with each case's latest status) · **Execution Details**
(per-run metadata, test table, failure messages, tracebacks, screenshots, report downloads) ·
**History & Analytics** (outcome and pass-rate trends, failures by module, frequently failing and
flaky cases, duration trend).

## Run tests from the dashboard

The panel at the top of the page has two triggers:

- **Run all tests** (local). It first checks that `<App base URL>/bank/login` responds. Set the URL in the
  sidebar; the default is `$BASE_URL` or `http://localhost:3000`. If the app isn't up, start it with
  `npm run build && npm start`. The button then runs `testing/.venv/bin/python -m pytest` in `testing/`
  with `BASE_URL` and `HEADLESS=1` set, and streams the output into the page. When pytest finishes,
  `testing/reports` is ingested automatically. The suite's venv must exist:
  `cd testing && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- **Trigger CI run.** Sends a `workflow_dispatch` for `selenium-tests.yml` on the branch set in the sidebar.
  It needs `GITHUB_TOKEN` with `actions: write`. When the run finishes, press **Sync from GitHub**.

## Ingest results

Use the sidebar buttons, or the CLI:

```bash
# after running pytest in testing/
dashboard/.venv/bin/python dashboard/ingest.py local            # default dir: testing/reports
dashboard/.venv/bin/python dashboard/ingest.py local path/to/reports

# pull the `test-results` artifact of recent selenium-tests.yml runs
GITHUB_TOKEN=... dashboard/.venv/bin/python dashboard/ingest.py github --limit 20

# retention: keep only the newest N runs
dashboard/.venv/bin/python dashboard/ingest.py prune --keep 200
```

Ingesting is keyed by `run_id` and is idempotent: re-ingesting the same run replaces it.
GitHub sync skips runs that are already stored (use `--force` to re-download them). It reports
expired or missing artifacts per run, and stops cleanly when it hits a rate limit.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | — | Token with `actions: read`. Needed to download artifacts, even from a public repo. Also read from `.streamlit/secrets.toml`. |
| `GITHUB_REPOSITORY` | `Adnan-Safdari/qa-playground-testing` | `owner/name` of the repo to sync from |
| `BANKTEST_DB_PATH` | `dashboard/data/history.db` | SQLite history |
| `BANKTEST_ARTIFACTS_DIR` | `<db dir>/artifacts` | Copied reports and screenshots, one folder per run |
| `BANKTEST_REPORTS_DIR` | `testing/reports` | Source for "Ingest local results" |
| `BANKTEST_CATALOGUE_PATH` | `testing/test_cases.json` | Test-case catalogue |

## Retention

GitHub Actions artifacts expire after **30 days**, so they are not a permanent store. Each
ingest copies the run's `results.json`, `report.html`, `junit.xml` and failure screenshots to
`dashboard/data/artifacts/<run_id>/` and normalises its results into SQLite (`runs`,
`test_results`). That copy is the long-term history. To keep a long history, sync at least once
every 30 days. Use `ingest.py prune --keep N` to limit how much is kept. `dashboard/data/*.db`
is git-ignored.

## Tests

```bash
dashboard/.venv/bin/pip install -r dashboard/requirements-dev.txt
dashboard/.venv/bin/python -m pytest dashboard/tests -q
```

The files in `tests/fixtures/` are used only by these unit tests. The app never loads them.
