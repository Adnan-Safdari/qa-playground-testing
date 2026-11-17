# BankTest

Continuous quality-assurance and regression-testing platform for a demo banking web application (Seleniverse 2.0 hackathon).

This repository contains the **Bank Demo App** (forked from QA Playground and stripped down to the banking app only) — the system under test. Selenium/Pytest tests, the GitHub Actions workflow, the Streamlit dashboard and Docker setup will be added alongside it. See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the full plan.

> This is a demo environment. No real money or real accounts are involved.

## Run the app

Requires Node.js 20+.

```bash
npm install
npm run dev          # http://localhost:3000  (redirects to /bank)
```

Production build:

```bash
npm run build
npm start
```

Login: `admin` / `admin123`

## Routes

| Route | Page |
|---|---|
| `/bank` | Login |
| `/bank/dashboard` | Balance summary, recent transactions |
| `/bank/accounts` | Account list, create / edit / delete |
| `/bank/accounts/[id]` | Account detail and statement |
| `/bank/transactions` | Create and filter transactions |
| `/bank/transactions/[id]` | Transaction detail |

All data is stored in the browser (`localStorage` for accounts and transactions, `sessionStorage` for the login session). There is no backend or database.

Selectors (`id`, `data-testid`, `data-action`) are documented in [app/(bank)/README.md](app/(bank)/README.md).
