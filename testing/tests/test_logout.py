"""Module: Logout (SB-LO-*)."""

import pytest

from pages import DashboardPage, LoginPage
from test_data import messages as msg
from test_data.users import STANDARD_USER

pytestmark = pytest.mark.logout


@pytest.mark.testcase("SB-LO-01")
def test_logout_shows_confirmation(login_as):
    dashboard = login_as(STANDARD_USER.username, STANDARD_USER.password)
    login = dashboard.logout()

    assert "reason=logged_out" in login.current_url
    assert login.message_text(LoginPage.LOGOUT_MESSAGE, msg.LOGGED_OUT) == msg.LOGGED_OUT
    assert login.is_visible(LoginPage.LOGIN_BUTTON)


@pytest.mark.testcase("SB-LO-02")
def test_protected_page_requires_login_after_logout(login_as, driver, base_url):
    login_as(STANDARD_USER.username, STANDARD_USER.password).logout()

    driver.get(f"{base_url}{DashboardPage.PATH}")
    login = LoginPage(driver, base_url)
    url = login.wait_url_contains("reason=auth")
    login.wait_until_loaded()

    assert LoginPage.PATH in url
    assert login.message_text(LoginPage.AUTH_REQUIRED_MESSAGE, msg.AUTH_REQUIRED) == msg.AUTH_REQUIRED
    assert not login.is_visible(DashboardPage.LOGOUT_BUTTON), "App shell rendered without a session"
