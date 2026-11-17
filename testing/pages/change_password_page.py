"""Change password — /bank/change-password."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.app_page import AppPage


class ChangePasswordPage(AppPage):
    PATH = "/bank/change-password"
    TITLE = "Change Password | SecureBank"

    CURRENT_PASSWORD = (By.ID, "current-password")
    NEW_PASSWORD = (By.ID, "new-password")
    CONFIRM_PASSWORD = (By.ID, "confirm-password")
    SUBMIT = (By.ID, "change-password-submit")

    CURRENT_PASSWORD_ERROR = (By.ID, "current-password-error")
    NEW_PASSWORD_ERROR = (By.ID, "new-password-error")
    CONFIRM_PASSWORD_ERROR = (By.ID, "confirm-password-error")
    SUCCESS = (By.ID, "password-success")

    READY_ELEMENT = SUBMIT

    ERRORS = {
        "current_password": CURRENT_PASSWORD_ERROR,
        "new_password": NEW_PASSWORD_ERROR,
        "confirm_password": CONFIRM_PASSWORD_ERROR,
    }

    def change_password(self, current: str, new: str, confirm: str | None = None) -> None:
        self.type(self.CURRENT_PASSWORD, current)
        self.type(self.NEW_PASSWORD, new)
        self.type(self.CONFIRM_PASSWORD, new if confirm is None else confirm)
        self.click(self.SUBMIT)

    def success_text(self, expected: str) -> str:
        return self.wait_text_equals(self.SUCCESS, expected)

    def field_values(self) -> dict:
        return {
            "current_password": self.value_of(self.CURRENT_PASSWORD),
            "new_password": self.value_of(self.NEW_PASSWORD),
            "confirm_password": self.value_of(self.CONFIRM_PASSWORD),
        }

    def error_text(self, field: str, expected: str | None = None) -> str:
        locator = self.ERRORS[field]
        if expected is not None:
            return self.wait_text_equals(locator, expected)
        self.wait_visible(locator)
        return self.text_of(locator)

    def is_success_shown(self) -> bool:
        return self.is_visible(self.SUCCESS)
