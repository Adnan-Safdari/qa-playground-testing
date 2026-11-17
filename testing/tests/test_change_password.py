"""Module: Change Password (SB-PW-*)."""

import pytest

from pages import ChangePasswordPage, DashboardPage, LoginPage
from test_data import messages as msg
from test_data import profile as data
from test_data.users import STANDARD_USER, WRONG_PASSWORD

pytestmark = pytest.mark.change_password


@pytest.fixture
def change_password_page(login_as, driver, base_url) -> ChangePasswordPage:
    login_as(STANDARD_USER.username, STANDARD_USER.password)
    return ChangePasswordPage(driver, base_url).open()


@pytest.mark.testcase("SB-PW-01")
def test_change_password_end_to_end(change_password_page, driver, base_url):
    page = change_password_page
    page.change_password(STANDARD_USER.password, data.NEW_PASSWORD)

    assert page.success_text(msg.PASSWORD_CHANGED) == msg.PASSWORD_CHANGED
    assert page.field_values() == {"current_password": "", "new_password": "", "confirm_password": ""}

    login = page.logout()
    error = login.login_expecting_error(STANDARD_USER.username, STANDARD_USER.password, msg.INVALID_CREDENTIALS)
    assert error == msg.INVALID_CREDENTIALS, "Old password must no longer work"

    dashboard = LoginPage(driver, base_url).open().login(STANDARD_USER.username, data.NEW_PASSWORD)
    assert DashboardPage.PATH in dashboard.current_url
    assert dashboard.current_username == STANDARD_USER.username


@pytest.mark.testcase("SB-PW-02")
def test_wrong_current_password(change_password_page):
    page = change_password_page
    page.change_password(WRONG_PASSWORD, data.NEW_PASSWORD)

    assert page.error_text("current_password", msg.CURRENT_PASSWORD_INCORRECT) == msg.CURRENT_PASSWORD_INCORRECT
    assert not page.is_success_shown()


@pytest.mark.testcase("SB-PW-03")
def test_confirmation_mismatch(change_password_page):
    page = change_password_page
    page.change_password(STANDARD_USER.password, data.NEW_PASSWORD, data.MISMATCHED_CONFIRMATION)

    assert page.error_text("confirm_password", msg.PASSWORDS_DO_NOT_MATCH) == msg.PASSWORDS_DO_NOT_MATCH
    assert not page.is_success_shown()


@pytest.mark.testcase("SB-PW-04")
def test_weak_new_password(change_password_page, driver, base_url):
    page = change_password_page
    page.change_password(STANDARD_USER.password, data.WEAK_NEW_PASSWORD)

    assert page.error_text("new_password", msg.PASSWORD_TOO_SHORT) == msg.PASSWORD_TOO_SHORT
    assert not page.is_success_shown()

    # The original password must still be valid.
    login = page.logout()
    dashboard = login.login(STANDARD_USER.username, STANDARD_USER.password)
    assert DashboardPage.PATH in dashboard.current_url
