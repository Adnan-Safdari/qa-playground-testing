"""Module: Open Application (SB-OP-*)."""

import pytest
import requests

from pages import LoginPage, NotFoundPage
from test_data import messages as msg

pytestmark = pytest.mark.open_application


@pytest.mark.testcase("SB-OP-01")
def test_application_loads_successfully(driver, base_url):
    response = requests.get(f"{base_url}{LoginPage.PATH}", timeout=30)
    assert response.status_code == 200, f"GET {LoginPage.PATH} returned HTTP {response.status_code}"

    page = LoginPage(driver, base_url).open()
    title = page.wait_title(LoginPage.TITLE)
    assert "SecureBank" in title
    assert title == LoginPage.TITLE
    assert page.current_url.startswith(page.url_for(LoginPage.PATH))


@pytest.mark.testcase("SB-OP-02")
def test_login_page_ui_elements_present(login_page):
    for name, locator in login_page.form_controls().items():
        element = login_page.wait_visible(locator)
        assert element.is_displayed(), f"{name} is not visible"
        assert element.is_enabled(), f"{name} is not enabled"

    assert login_page.find(LoginPage.PASSWORD).get_attribute("type") == "password", \
        "Password must be masked by default"
    assert login_page.is_visible(LoginPage.CREATE_ACCOUNT_LINK), "Create-account link is missing"


@pytest.mark.testcase("SB-OP-03")
def test_invalid_url_shows_page_not_found(driver, base_url):
    response = requests.get(f"{base_url}{NotFoundPage.PATH}", timeout=30)
    assert response.status_code == 404, f"GET {NotFoundPage.PATH} returned HTTP {response.status_code}"

    page = NotFoundPage(driver, base_url).open()
    assert page.heading == msg.PAGE_NOT_FOUND
    assert page.wait_title(NotFoundPage.TITLE) == NotFoundPage.TITLE
