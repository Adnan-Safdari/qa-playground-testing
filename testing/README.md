# SecureBank Selenium + Pytest suite (BankTest)

Regression suite for the SecureBank demo app. Selectors, routes and messages come from
[`APP_CONTRACT.md`](APP_CONTRACT.md); the manual catalogue is [`test_cases.json`](test_cases.json).

## Run locally

```bash
# 1. start the app (repo root)
npm install && npm run build && npm start          # http://localhost:3000

# 2. run the tests (from testing/)
cd testing
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest                                   # all tests, headless Chrome
HEADLESS=0 pytest -k transfer            # watch the browser, one module
pytest -m critical                       # Critical cases only
python scripts/quality_gate.py           # CI gate on reports/results.json
```

Chrome must be installed; Selenium Manager downloads the matching chromedriver.

| Env var | Default | Purpose |
|---|---|---|
| `BASE_URL` | `http://localhost:3000` | App under test |
| `HEADLESS` | `1` | `0` shows the browser |
| `WINDOW_SIZE` | `1440x900` | Browser window size |
| `BROWSER` | `chrome` | Only Chrome is supported |
| `CHROME_BINARY` | auto | Custom Chrome executable |
| `EXPLICIT_WAIT` | `10` | Default explicit wait (s); implicit wait is 0, no `time.sleep` |
| `PAGE_LOAD_TIMEOUT` | `60` | Driver page-load timeout (s) |
| `MIN_PASS_RATE` | `0` | Quality gate pass-rate threshold % (0 = off) |

Each test gets its own Chrome (fresh localStorage = freshly seeded bank data).

## Output (`reports/`, git-ignored, uploaded by CI as `test-results`)

`junit.xml`, `report.html` (self-contained, screenshots embedded), `results.json`
(schema in APP_CONTRACT.md §4), `screenshots/<tc_id>_<UTC>.png` for failures, and in CI `server.log`.

## Layout

```
conftest.py          driver + login/register fixtures, registers the results plugin
pages/               Page Object Model — every selector lives here
tests/               one file per module, each test tagged @pytest.mark.testcase("SB-XX-NN")
test_data/           users, customers, transfer/profile data, exact expected messages
utils/               results.json plugin, full-page screenshots, money formatting
scripts/quality_gate.py   fails CI on any Critical failure / low pass rate
test_cases.json      manual test-case catalogue (title/module/priority source)
```

Every test must carry a `testcase` marker whose ID exists in `test_cases.json`; collection
fails otherwise. Priority `Critical` cases are auto-marked `critical`.
