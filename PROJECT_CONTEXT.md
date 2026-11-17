BankTest --- Project Context
1. Project Overview
BankTest is a continuous quality-assurance and regression-testing
platform for the QA Playground banking web application.

The project combines manual test planning, automated browser testing, CI
execution, and test-result reporting. Its goal is to verify both user
workflows and important banking business rules, and to make failures
easy to investigate.

The project is being developed for the Seleniverse 2.0
software-testing hackathon.
2. Core Idea
Whenever code is pushed to the GitHub repository, or a pull request is
opened, GitHub Actions should automatically:
1. Check out the repository.
2. Install the application's dependencies.
3. Build and start the banking application in the CI environment.
4. Run the Selenium test suite through Pytest.
5. Collect pass/fail results, execution times, logs, and failure
   screenshots.
6. Generate a test report and retain the results as CI artifacts.
7. Apply a quality gate so critical test failures can fail the
   workflow.
A Streamlit dashboard will present test results and execution history in
an accessible interface.
3. Repository Strategy
Use one repository (a monorepo): fork the original QA Playground
repository and add the BankTest testing and dashboard components to that
fork.

This keeps the application and its tests together. A code change and its
related regression tests can be reviewed and executed in the same pull
request.

Do not create a separate testing repository unless the project scope
changes later.
4. Proposed Repository Structure
The exact existing application folders should be preserved. Add the
following project folders at the repository root:
qa-playground/
├── <existing Next.js application files>
├── testing/
│   ├── tests/
│   │   ├── test_login.py
│   │   ├── test_accounts.py
│   │   ├── test_transactions.py
│   │   └── test_logout.py
│   ├── test_data/
│   ├── screenshots/
│   ├── reports/
│   ├── conftest.py
│   ├── pytest.ini
│   └── requirements.txt
├── dashboard/
│   └── app.py
└── .github/
    └── workflows/
        └── selenium-tests.yml
Generated screenshots and reports should be handled deliberately: retain
useful CI artifacts, but avoid committing transient output files to Git.
5. Technology Stack
  Area                    Technology              Purpose
  Application under test  Existing QA Playground  Banking web application
app (Next.js)           

  Browser automation      Selenium WebDriver      Automate browser
interactions

  Test framework          Pytest                  Organise, execute, and
assert test cases

  Continuous integration  GitHub Actions          Trigger tests on pushes
and pull requests

  Dashboard               Streamlit               Present test results
and trends

  Charts                  Plotly                  Visualise test metrics

  Result storage          SQLite (if needed)      Store execution history
for the dashboard
Reports                 pytest-html or a custom Share execution details
HTML report
Prefer explicit Selenium waits over fixed sleeps. Keep selectors
centralised where practical so changes to the application UI are easier
to maintain.
6. Functional Test Scope
The hackathon brief identifies two main workflows.
Test Plan 1 --- Account Creation and Money Transfer
Test the applicable account-creation flow, login, money transfer,
transaction result, and logout.

Representative cases:
- Open the application.
- Create an account using valid details.
- Validate required fields and invalid input.
- Reject duplicate account details where applicable.
- Log in with valid and invalid credentials.
- Complete a valid transfer.
- Reject zero, negative, or excessive transfer amounts.
- Verify sender and recipient balances.
- Verify transaction history.
- Log out and verify protected pages are not accessible.
Test Plan 2 --- Profile Management and Password Change
Test the profile-editing and password-change workflow requested in the
hackathon brief.

Representative cases:
- Log in.
- Open the profile page.
- Update valid profile information.
- Validate missing or invalid profile fields.
- Change the password using the correct current password.
- Reject an incorrect current password.
- Reject mismatched or invalid new passwords.
- Verify login with the new password and rejection of the old
  password.
- Log out and verify session protection.
Application capability check: Before automating a case, inspect the
forked application's current implementation and confirm that the feature
exists. The repository documentation previously reviewed described
account management and transactions, but did not establish that profile
editing, password changing, or public user registration are implemented.
Do not invent selectors or claim unsupported features work. Mark
unavailable functionality as blocked/not applicable and report the gap
clearly.
7. Test Design Principles
Each test case should record:
- Test case ID
- Feature/module
- Title and objective
- Preconditions
- Test data
- Steps
- Expected result
- Actual result
- Priority/risk
- Execution status
- Evidence or failure details
Use positive, negative, boundary, and regression tests.

Prioritise cases by business impact. Money transfers, authentication,
and session handling should receive particular attention.
Banking Business-Rule Validation
Do not rely only on success messages. Where the application exposes
reliable data, verify the underlying result.

Example:
- Sender opening balance: 5,000
- Recipient opening balance: 2,500
- Transfer: 500
- Expected sender balance: 4,500
- Expected recipient balance: 3,000
- Expected combined balance: 7,500
Also verify the transaction record. Use isolated test data and reset or
prepare the test state so repeated CI runs remain reliable.

The application is a test/demo banking environment; tests must not be
represented as real-money transactions.
8. CI/CD Workflow
Triggers
- Push to the main branch.
- Pull requests targeting the main branch.
- Manual workflow dispatch.
- Optional scheduled nightly regression run.
Workflow stages
1. Checkout: Get the commit being tested.
2. Setup: Install supported Node.js and Python versions.
3. Install: Install application and Python test dependencies.
4. Build: Build the Next.js application.
5. Start: Launch the application in the CI runner and wait for its
   health/readiness check.
6. Test: Run Pytest with Selenium using headless Chrome.
7. Collect: Save JUnit XML, HTML report, logs, and failure
   screenshots.
8. Publish: Upload reports and screenshots as GitHub Actions
   artifacts.
9. Quality gate: Fail the workflow when critical tests fail or
   configured acceptance criteria are not met.
The CI job should test the checked-out local build, not depend on the
public demo site. This makes runs more repeatable and ensures the tests
validate the commit that triggered the workflow.
9. Streamlit Dashboard
The dashboard should focus on useful QA information rather than
decoration.
Overview
- Total tests
- Passed, failed, skipped, and blocked tests
- Pass percentage
- Total and average execution duration
- Latest run status
- Recent execution history
Test Management
- List test cases by module and priority.
- Show expected results and current status.
- Filter by feature, priority, and outcome.
Execution Details
- Commit SHA, branch, and workflow run
- Individual test outcomes and durations
- Failure messages and stack traces
- Links to or previews of failure screenshots
- Downloadable test reports
History and Analytics
- Pass/fail trend across runs
- Failure count by module
- Frequently failing test cases
- Execution-duration trend
The dashboard can retrieve run metadata and artifacts through the GitHub
API. If historical analytics are required, store normalised execution
results in SQLite. Do not assume GitHub Actions artifacts are a
permanent database; define an appropriate retention policy.
10. Demonstration Feature: Regression Bug Detection
Prepare a controlled demonstration:
1. Run the test suite against a working application and show passing
   tests.
2. Introduce a deliberate, harmless bug in the fork, such as a
   test-only change that causes a transfer validation rule to fail.
3. Push the change or open a pull request.
4. Show GitHub Actions triggering automatically.
5. Show Selenium detecting the regression.
6. Show the failed test, error details, and screenshot in the
   report/dashboard.
7. Revert or fix the change and rerun the workflow to show the tests
   passing.
Clearly label the bug as intentionally introduced for demonstration. Do
not damage shared or production systems.
11. Development Milestones
Build in this order:
1. Fork the application and run it locally.
2. Inspect the actual routes, UI elements, and supported features.
3. Write manual test cases for the supported requirements.
4. Create a Pytest structure and automate the highest-priority
   workflows.
5. Verify assertions and repeatability locally.
6. Configure GitHub Actions to build, start, and test the application.
7. Capture failure screenshots and publish reports as artifacts.
8. Build the Streamlit dashboard.
9. Add GitHub run history and analytics.
10. Prepare the regression demonstration and presentation.
The automation engine and reliable tests take priority over dashboard
styling.
12. Definition of Done
The project is ready for demonstration when:
- The forked application runs locally.
- Manual test cases have clear steps and expected results.
- Automated tests execute reliably against the local application.
- Pushes and pull requests trigger GitHub Actions.
- CI starts the application and runs the tests against that commit.
- Failures produce useful diagnostics and screenshots.
- Reports are available as workflow artifacts.
- The dashboard displays real execution data, not hardcoded sample
  metrics.
- Unsupported application features are identified honestly.
- A controlled regression can be detected and then cleared by a fix.
13. Project Principles
- Test actual application behaviour; do not fabricate features or
  selectors.
- Validate business logic, not just page navigation and button clicks.
- Keep tests repeatable, isolated, and safe to rerun.
- Use explicit waits and meaningful assertions.
- Keep secrets out of source code and logs.
- Make reports traceable to a commit and workflow run.
- Prefer a small, reliable end-to-end system over many unfinished
  features.
Project name: BankTest
Description: Continuous Quality Assurance and Regression Testing
Platform for a banking web application.
Repository approach: Single-repository monorepo based on a fork of
QA Playground.
Primary outcome: Automatically test application changes with
Selenium and Pytest through GitHub Actions, then present trustworthy
results and evidence in a Streamlit dashboard.