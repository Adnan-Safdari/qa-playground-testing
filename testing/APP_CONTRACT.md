# SecureBank — App ↔ Tests ↔ Dashboard Contract

Single source of truth shared by the UI, the Selenium/Pytest suite and the Streamlit dashboard.
**Change this file first** if anything below must change, and tell the other owners.

## 1. Application under test

- Next.js app, fully client-side. All data is in the browser:
  - `localStorage["securebank:db:v1"]` — users, accounts, transactions (money stored as integer cents)
  - `localStorage["securebank:remember"]` — remembered login
  - `sessionStorage["securebank:session"]` — logged-in username
- A fresh browser profile = fresh seeded data. Tests isolate state by using a new driver per test
  **or** by running `localStorage.clear(); sessionStorage.clear();` on the app origin before each test.
- Base URL from env `BASE_URL`, default `http://localhost:3000`.
- Run locally: `npm install && npm run build && npm start` (port 3000).
- Theme defaults to light.

### Seeded users (password `bank_sauce` for all)

| Username | Email | Full name | Behaviour | Accounts (number — nickname — balance) |
|---|---|---|---|---|
| standard_user | alex.morgan@example.com | Alex Morgan | Full access | 1002003001 — Everyday Checking — $12,450.00; 1002003002 — High-Yield Savings — $4,600.00 |
| locked_user | jordan.lee@example.com | Jordan Lee | Login rejected | 1002004001 — Everyday Checking — $3,200.00 |
| frozen_user | sam.rivera@example.com | Sam Rivera | Transfers rejected | 1002005001 — $5,400.00; 1002005002 — $2,100.00 |
| overdraft_user | casey.kim@example.com | Casey Kim | Negative balance | 1002006001 — -$250.00; 1002006002 — $80.00 |
| slow_user | taylor.brooks@example.com | Taylor Brooks | Every app page shows `#page-loader` for 2.5 s before content | 1002007001 — $7,300.00; 1002007002 — $1,500.00 |

Login accepts **username or email** (case-insensitive email).

## 2. Routes

| Route | Purpose | `document.title` |
|---|---|---|
| `/` | redirects to `/bank/login` | — |
| `/bank` | redirects to `/bank/login` | — |
| `/bank/login` | Login | `Sign in \| SecureBank` |
| `/bank/register` | Create a new customer account (public) | `Create Account \| SecureBank` |
| `/bank/dashboard` | Dashboard (protected) | `Dashboard \| SecureBank` |
| `/bank/accounts` | Account list (protected) | `Accounts \| SecureBank` |
| `/bank/accounts/open` | Open an additional account (protected) | `Open Account \| SecureBank` |
| `/bank/transfer` | Money transfer (protected) | `Transfer \| SecureBank` |
| `/bank/transactions` | Transaction history (protected) | `Transactions \| SecureBank` |
| `/bank/profile` | Edit profile (protected) | `Profile \| SecureBank` |
| `/bank/change-password` | Change password (protected) | `Change Password \| SecureBank` |
| anything else, e.g. `/bank/invalid` | HTTP **404**, `[data-testid="not-found"]`, `h1` text `Page not found` | `Page not found \| SecureBank` |

Protected route without a session → redirect to `/bank/login?reason=auth`.

Every element below has the same value for `id` and `data-testid` unless noted.
Every protected page has `#page-title` (an `h1`).

## 3. Selectors and messages

### Login — `/bank/login`
- `#username`, `#password`, `#toggle-password` (show/hide), `#remember-me` (native checkbox), `#login-button`
- `#create-account-link` → `/bank/register`
- Errors: `#username-error` "Username is required." · `#password-error` "Password is required." · `#login-error` "Invalid username or password." / "Your account has been locked. Please contact support."
- `#logout-message` "You have been logged out." (shown for `?reason=logged_out`)
- `#auth-required-message` "Please sign in to continue." (shown for `?reason=auth`)
- `#test-credentials` table; `#reset-demo-data` button (clears all storage, reseeds)
- On success → `/bank/dashboard`

### Register — `/bank/register`
- `#full-name`, `#email`, `#password`, `#initial-deposit`, `#register-button`, `#login-link`
- Rules + exact messages:
  - Full name: `#full-name-error` "Full name is required." / "Full name must be 2–50 characters." / "Full name can only contain letters, spaces, . ' and -."
  - Email: `#email-error` "Email is required." / "Enter a valid email address." / "An account already exists with this email."
  - Password: `#password-error` "Password is required." / "Password must be at least 8 characters." / "Password must contain at least one letter and one number."
  - Initial deposit: `#initial-deposit-error` "Initial deposit is required." / "Enter a valid amount." / "Minimum initial deposit is $25.00." / "Maximum initial deposit is $100,000.00."
- Success: form replaced by `#register-success` containing text "Account created successfully", `#new-account-number` (10 digits), `#new-account-balance`; user is logged in; `#go-to-dashboard` link.
- The new user's username is their email (lower-cased); they get one checking account "Everyday Checking" funded with the initial deposit. New account numbers are sequential: `1009000001`, `1009000002`, … per browser.

### App shell (all protected pages)
- `#logout-button` → clears session, goes to `/bank/login?reason=logged_out`
- `#theme-toggle`, `#current-username`, `#user-full-name`, `#mobile-menu-toggle`
- Nav: `#nav-dashboard`, `#nav-accounts`, `#nav-open-account`, `#nav-transfer`, `#nav-transactions`, `#nav-profile`, `#nav-change-password`
- `#page-loader` while loading (slow_user)

### Dashboard — `/bank/dashboard`
- `#page-title` "Welcome back, {first name}"
- Stat values (each has `data-cents`): `#stat-net-worth`, `#stat-net-change`, `#stat-income`, `#stat-expenses`; `#stat-account-count` text "Across N accounts"
- Quick actions: `#qa-open-account`, `#qa-transfer`, `#qa-transactions`, `#qa-profile`, `#qa-change-password`
- `#recent-transactions` table, rows `[data-testid="recent-transaction-row"]`; `#view-all-transactions`

### Accounts — `/bank/accounts`
- `#open-account-button`
- Each account: `[data-testid="account-card"][data-account-number="1002003001"]` containing
  `[data-testid="account-nickname"]`, `[data-testid="account-type"]` (Checking/Savings), `[data-testid="account-number"]` (full 10-digit number), `[data-testid="account-balance"]` (text like `$12,450.00`, attribute `data-cents`)

### Open account — `/bank/accounts/open`
- `#account-type` (native `<select>`, values `checking`/`savings`, placeholder value ``), `#nickname`, `#initial-deposit`, `#accept-terms`, `#open-account-submit`
- Errors: `#account-type-error` "Select an account type." · `#nickname-error` "Account nickname is required." / "Nickname must be 3–30 characters." / "You already have an account with this nickname." · `#initial-deposit-error` (same messages as register) · `#accept-terms-error` "You must accept the terms and conditions."
- Success: `#open-account-success`, `#new-account-number`, `#open-another-account`, `#view-accounts`

### Transfer — `/bank/transfer`
- `#from-account` (native `<select>`, option **value = account number**, placeholder value ``), `#available-balance` (balance of selected from-account, `data-cents`)
- `#to-account` (text input: recipient **account number**, any customer's account), `#amount`, `#memo` (optional, ≤ 50 chars), `#transfer-submit`
- Errors and exact messages:
  - `#from-account-error` "Select the account to transfer from."
  - `#to-account-error` "Recipient account number is required." / "Recipient account not found." / "You cannot transfer to the same account."
  - `#amount-error` "Amount is required." / "Amount must be greater than zero." (0, 0.00) / "Enter a valid amount." (negative, non-numeric, >2 decimals) / "Insufficient balance." / "Transfers are limited to $10,000.00 per transaction."
  - `#memo-error` "Memo must be 50 characters or fewer."
  - `#transfer-error` (form level) "Your accounts are frozen. Transfers are disabled — please contact support."
  - `#frozen-notice` banner shown on page for frozen_user
- Success: form replaced by `#transfer-success` containing "Transfer successful", `#transfer-reference` (e.g. `TRF100123`), `#transfer-amount`, `#transfer-from-account`, `#transfer-to-account`, `#transfer-new-balance` (sender's new balance, `data-cents`); `#new-transfer-button`, `#view-transactions-link`
- Business rules: sender balance −amount, recipient balance +amount, two transaction rows sharing one reference.

### Transactions — `/bank/transactions`
- `#account-filter` (native `<select>`, value `` = all, otherwise account number)
- `#transactions-table`; rows `[data-testid="transaction-row"]` newest first, attributes `data-reference` (transfers only), `data-account-number`
- Cells: `[data-testid="transaction-date"]`, `[data-testid="transaction-description"]`, `[data-testid="transaction-account"]` (full number), `[data-testid="transaction-category"]`, `[data-testid="transaction-amount"]` (`data-cents`, signed), `[data-testid="transaction-balance"]`
- Transfer descriptions: sender row "Transfer to 1009000002", recipient row "Transfer from 1009000001" (+ " — {memo}" if memo given). Category "Transfer".
- `#no-transactions` empty state

### Profile — `/bank/profile`
- `#profile-username` (read-only), `#full-name`, `#email`, `#phone`, `#address`, `#save-profile`
- Errors: `#full-name-error` (as register) · `#email-error` "Email is required." / "Enter a valid email address." / "An account already exists with this email." · `#phone-error` "Phone number is required." / "Enter a valid phone number (10–15 digits)." · `#address-error` "Address must be 100 characters or fewer."
- Success: `#profile-success` "Profile updated successfully." (sidebar `#user-full-name` updates)

### Change password — `/bank/change-password`
- `#current-password`, `#new-password`, `#confirm-password`, `#change-password-submit`
- Errors: `#current-password-error` "Current password is required." / "Current password is incorrect." · `#new-password-error` "New password is required." / "Password must be at least 8 characters." / "Password must contain at least one letter and one number." / "New password must be different from the current password." · `#confirm-password-error` "Please confirm the new password." / "Passwords do not match."
- Success: `#password-success` "Password changed successfully." Fields cleared. Old password no longer logs in; new one does.

## 4. Test result files (tests → dashboard)

Written by the pytest suite on every run, in `testing/reports/` (git-ignored, uploaded as CI artifact `test-results`):

- `junit.xml` — standard JUnit XML
- `report.html` — pytest-html self-contained report
- `results.json` — schema below
- `screenshots/<tc_id>_<timestamp>.png` — one per failed test

```json
{
  "schema_version": 1,
  "run": {
    "run_id": "local-20261117T120000Z or GitHub run id",
    "started_at": "2026-11-17T12:00:00Z",
    "finished_at": "2026-11-17T12:03:10Z",
    "duration_seconds": 190.2,
    "commit_sha": "abc123… (GITHUB_SHA or git rev-parse HEAD, else null)",
    "branch": "main (GITHUB_REF_NAME or git branch, else null)",
    "workflow_run_id": "123456 or null",
    "workflow_run_url": "https://github.com/<owner>/<repo>/actions/runs/123456 or null",
    "trigger": "push | pull_request | workflow_dispatch | schedule | local",
    "base_url": "http://localhost:3000",
    "browser": "chrome 131.0",
    "headless": true
  },
  "summary": { "total": 25, "passed": 23, "failed": 1, "skipped": 1, "error": 0, "pass_rate": 95.83, "critical_failed": 0 },
  "tests": [
    {
      "tc_id": "SB-TR-01",
      "title": "Successful money transfer",
      "module": "Money Transfer",
      "priority": "Critical",
      "nodeid": "tests/test_transfer.py::test_successful_transfer",
      "outcome": "passed | failed | skipped | error",
      "duration_seconds": 4.21,
      "message": "short failure message or null",
      "traceback": "full traceback or null",
      "screenshot": "screenshots/SB-TR-01_20261117T120105Z.png or null"
    }
  ]
}
```

`pass_rate` = passed / (total − skipped) × 100, rounded to 2 decimals (0 when denominator is 0).

## 5. Test-case catalogue (tests → dashboard)

`testing/test_cases.json` — the manual test-case catalogue, a JSON array:

```json
[{
  "tc_id": "SB-TR-01", "module": "Money Transfer", "title": "Successful money transfer",
  "objective": "…", "preconditions": "…", "test_data": "…",
  "steps": ["…", "…"], "expected_result": "…",
  "priority": "Critical | High | Medium | Low", "automated": true,
  "status": "Automated | Blocked | Not Applicable", "notes": "…"
}]
```

Modules: `Open Application`, `Create New Account`, `Money Transfer`, `Authentication`, `Logout`, `Profile`, `Change Password`.
