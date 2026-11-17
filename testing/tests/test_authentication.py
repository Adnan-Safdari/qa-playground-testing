"""Module: Authentication (SB-AU-*)."""

import pytest

from pages import DashboardPage, LoginPage
from test_data import messages as msg
from test_data.users import LOCKED_USER, SLOW_USER, STANDARD_USER, WRONG_PASSWORD

pytestmark = pytest.mark.authentication


@pytest.mark.testcase("SB-AU-01")
def test_valid_login(login_page):
    dashboard = login_page.login(STANDARD_USER.username, STANDARD_USER.password)

    assert DashboardPage.PATH in dashboard.current_url
    assert dashboard.wait_title(DashboardPage.TITLE) == DashboardPage.TITLE
    assert dashboard.page_title == f"Welcome back, {STANDARD_USER.first_name}"
    assert dashboard.current_username == STANDARD_USER.username
    assert dashboard.account_count_text == f"Across {len(STANDARD_USER.accounts)} accounts"


@pytest.mark.testcase("SB-AU-02")
def test_invalid_password_rejected(login_page):
    error = login_page.login_expecting_error(STANDARD_USER.username, WRONG_PASSWORD, msg.INVALID_CREDENTIALS)

    assert error == msg.INVALID_CREDENTIALS
    assert LoginPage.PATH in login_page.current_url
    assert DashboardPage.PATH not in login_page.current_url


@pytest.mark.testcase("SB-AU-03")
def test_locked_user_rejected(login_page):
    error = login_page.login_expecting_error(LOCKED_USER.username, LOCKED_USER.password, msg.ACCOUNT_LOCKED)

    assert error == msg.ACCOUNT_LOCKED
    assert LoginPage.PATH in login_page.current_url


@pytest.mark.testcase("SB-AU-04")
def test_slow_user_dashboard_loads_with_explicit_waits(login_page, driver, base_url):
    login_page.submit_credentials(SLOW_USER.username, SLOW_USER.password)

    dashboard = DashboardPage(driver, base_url)
    dashboard.wait_url_contains(DashboardPage.PATH)
    # The loader is shown for ~2.5 s; wait for it explicitly rather than sleeping.
    assert dashboard.wait_for_loader_to_disappear(), "#page-loader never disappeared"
    dashboard.wait_until_loaded()

    assert dashboard.page_title == f"Welcome back, {SLOW_USER.first_name}"
    assert dashboard.current_username == SLOW_USER.username
    assert dashboard.account_count_text == f"Across {len(SLOW_USER.accounts)} accounts"
