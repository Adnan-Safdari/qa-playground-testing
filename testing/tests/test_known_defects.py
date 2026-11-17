"""Module: Known Defects (SB-KD-*).

Requirements SecureBank does NOT meet yet. These tests are EXPECTED TO FAIL: each failure
produces a screenshot and a bug report (reports/bug_reports/<tc_id>.md + the dashboard's
Bug Reports tab). None is Critical, so the CI quality gate is not affected.

Skip them with:  pytest -m "not known_defect"
"""

import pytest

from pages import AccountsPage, DashboardPage, TransferPage
from test_data import customers
from test_data.users import STANDARD_USER

pytestmark = pytest.mark.known_defect

STD_CHECKING, STD_SAVINGS = list(STANDARD_USER.accounts)
LOCKED_MESSAGE = "Your account has been locked. Please contact support."


@pytest.mark.testcase("SB-KD-01")
def test_account_locks_after_three_failed_logins(login_page):
    invalid = "Invalid username or password."
    login_page.submit_credentials(STANDARD_USER.username, "wrong_password_1")
    assert login_page.wait_for_login_outcome() == invalid
    for attempt in (2, 3):
        login_page.submit_credentials(STANDARD_USER.username, f"wrong_password_{attempt}")
        login_page.wait_text_equals(login_page.LOGIN_ERROR, invalid)

    login_page.submit_credentials(STANDARD_USER.username, STANDARD_USER.password)
    outcome = login_page.wait_for_login_outcome(stale_error=invalid)
    if outcome == "dashboard":
        DashboardPage(login_page.driver, login_page.base_url).wait_until_loaded()  # screenshot shows the dashboard
    assert outcome == LOCKED_MESSAGE, (
        f"No brute-force lockout: after 3 failed attempts the correct password still signed in "
        f"(outcome: {outcome!r}); expected {LOCKED_MESSAGE!r}."
    )


@pytest.mark.testcase("SB-KD-02")
def test_transfer_requires_confirmation_step(login_as, driver, base_url):
    login_as(STANDARD_USER.username, STANDARD_USER.password)
    page = TransferPage(driver, base_url).open()
    page.transfer(STD_CHECKING, STD_SAVINGS, "250")

    shown = page.wait_for_confirmation_or_receipt()
    assert shown == "confirm", (
        "Funds moved immediately on submit — no 'Confirm transfer' review step was shown "
        "(expected #transfer-confirm before any money moves)."
    )


@pytest.mark.testcase("SB-KD-03")
def test_account_numbers_are_masked(login_as, driver, base_url):
    login_as(STANDARD_USER.username, STANDARD_USER.password)
    card = AccountsPage(driver, base_url).open().account(STD_CHECKING)

    expected = f"•••• {STD_CHECKING[-4:]}"
    assert card.number == expected, (
        f"Full account number is displayed on the Accounts page: {card.number!r}; expected masked {expected!r}."
    )


@pytest.mark.testcase("SB-KD-04")
def test_single_account_label_grammar(register_customer, driver, base_url):
    register_customer(customers.sender("1000"), logout=False)
    dashboard = DashboardPage(driver, base_url).open()

    assert dashboard.account_count_text == "Across 1 account", (
        f"Dashboard caption has a grammar bug: {dashboard.account_count_text!r}; expected 'Across 1 account'."
    )
