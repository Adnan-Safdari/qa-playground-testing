"""Login page — /bank/login."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class LoginPage(BasePage):
    PATH = "/bank/login"
    TITLE = "Sign in | SecureBank"

    USERNAME = (By.ID, "username")
    PASSWORD = (By.ID, "password")
    TOGGLE_PASSWORD = (By.ID, "toggle-password")
    REMEMBER_ME = (By.ID, "remember-me")
    LOGIN_BUTTON = (By.ID, "login-button")
    CREATE_ACCOUNT_LINK = (By.ID, "create-account-link")

    USERNAME_ERROR = (By.ID, "username-error")
    PASSWORD_ERROR = (By.ID, "password-error")
    LOGIN_ERROR = (By.ID, "login-error")
    LOGOUT_MESSAGE = (By.ID, "logout-message")
    AUTH_REQUIRED_MESSAGE = (By.ID, "auth-required-message")

    TEST_CREDENTIALS = (By.ID, "test-credentials")
    RESET_DEMO_DATA = (By.ID, "reset-demo-data")

    READY_ELEMENT = LOGIN_BUTTON

    def submit_credentials(self, username: str, password: str) -> None:
        self.type(self.USERNAME, username)
        self.type(self.PASSWORD, password)
        self.click(self.LOGIN_BUTTON)

    def login(self, username: str, password: str):
        """Log in and return the loaded DashboardPage."""
        from pages.dashboard_page import DashboardPage

        self.submit_credentials(username, password)
        dashboard = DashboardPage(self.driver, self.base_url, self.timeout)
        dashboard.wait_url_contains(DashboardPage.PATH)
        return dashboard.wait_until_loaded()

    def login_expecting_error(self, username: str, password: str, expected: str) -> str:
        """Submit credentials that must be rejected; return the `#login-error` text."""
        self.submit_credentials(username, password)
        return self.wait_text_equals(self.LOGIN_ERROR, expected)

    def wait_for_login_outcome(self, stale_error: str | None = None) -> str:
        """After submit: 'dashboard' if the user got in, otherwise the `#login-error` text.

        `stale_error`: an error still on screen from the previous attempt, ignored while waiting.
        """

        def settled(d):
            if "/bank/dashboard" in d.current_url:
                return True
            try:  # the page may be navigating away mid-check
                return self.is_visible(self.LOGIN_ERROR) and self.text_of(self.LOGIN_ERROR) != stale_error
            except Exception:
                return False

        self._wait().until(settled)
        return "dashboard" if "/bank/dashboard" in self.driver.current_url else self.text_of(self.LOGIN_ERROR)

    def message_text(self, locator, expected: str) -> str:
        return self.wait_text_equals(locator, expected)

    def form_controls(self) -> dict:
        return {
            "username": self.USERNAME,
            "password": self.PASSWORD,
            "login button": self.LOGIN_BUTTON,
        }
