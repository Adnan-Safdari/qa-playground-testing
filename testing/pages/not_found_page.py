"""404 page — any unknown route, e.g. /bank/invalid."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class NotFoundPage(BasePage):
    PATH = "/bank/invalid"
    TITLE = "Page not found | SecureBank"

    CONTAINER = (By.CSS_SELECTOR, '[data-testid="not-found"]')
    # The h1 may be the container itself or a descendant of it.
    HEADING = (By.XPATH, "//*[@data-testid='not-found']/descendant-or-self::h1")

    READY_ELEMENT = CONTAINER

    def wait_until_loaded(self):
        self.wait_visible(self.CONTAINER)
        return self

    @property
    def heading(self) -> str:
        return self.text_of(self.HEADING)
