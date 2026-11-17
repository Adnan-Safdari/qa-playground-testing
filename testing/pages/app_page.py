"""App shell shared by every protected SecureBank page (sidebar, header, loader)."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class AppPage(BasePage):
    """Base for protected pages. Waits out `#page-loader` (slow_user) before use."""

    PAGE_LOADER = (By.ID, "page-loader")
    PAGE_TITLE = (By.ID, "page-title")

    LOGOUT_BUTTON = (By.ID, "logout-button")
    THEME_TOGGLE = (By.ID, "theme-toggle")
    CURRENT_USERNAME = (By.ID, "current-username")
    USER_FULL_NAME = (By.ID, "user-full-name")
    MOBILE_MENU_TOGGLE = (By.ID, "mobile-menu-toggle")

    NAV_DASHBOARD = (By.ID, "nav-dashboard")
    NAV_ACCOUNTS = (By.ID, "nav-accounts")
    NAV_OPEN_ACCOUNT = (By.ID, "nav-open-account")
    NAV_TRANSFER = (By.ID, "nav-transfer")
    NAV_TRANSACTIONS = (By.ID, "nav-transactions")
    NAV_PROFILE = (By.ID, "nav-profile")
    NAV_CHANGE_PASSWORD = (By.ID, "nav-change-password")

    # slow_user shows the loader for 2.5 s on every page; allow generous headroom.
    LOADER_TIMEOUT = 15

    def wait_until_loaded(self):
        self.wait_for_loader_to_disappear()
        self.wait_visible(self.PAGE_TITLE)
        if self.TITLE:
            self.wait_title(self.TITLE)
        ready = self.READY_ELEMENT or self.LOGOUT_BUTTON
        self.wait_visible(ready)
        self.wait_hydrated(ready)
        return self

    def wait_for_loader_to_disappear(self, timeout: float | None = None) -> bool:
        return self.wait_invisible(self.PAGE_LOADER, timeout or self.LOADER_TIMEOUT)

    @property
    def page_title(self) -> str:
        return self.text_of(self.PAGE_TITLE)

    @property
    def current_username(self) -> str:
        return self.text_of(self.CURRENT_USERNAME)

    @property
    def user_full_name(self) -> str:
        return self.text_of(self.USER_FULL_NAME)

    def logout(self):
        from pages.login_page import LoginPage

        self.click(self.LOGOUT_BUTTON)
        login = LoginPage(self.driver, self.base_url, self.timeout)
        login.wait_url_contains("/bank/login")
        return login.wait_until_loaded()
