"""Edit profile — /bank/profile."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.app_page import AppPage


class ProfilePage(AppPage):
    PATH = "/bank/profile"
    TITLE = "Profile | SecureBank"

    USERNAME = (By.ID, "profile-username")
    FULL_NAME = (By.ID, "full-name")
    EMAIL = (By.ID, "email")
    PHONE = (By.ID, "phone")
    ADDRESS = (By.ID, "address")
    SAVE = (By.ID, "save-profile")

    FULL_NAME_ERROR = (By.ID, "full-name-error")
    EMAIL_ERROR = (By.ID, "email-error")
    PHONE_ERROR = (By.ID, "phone-error")
    ADDRESS_ERROR = (By.ID, "address-error")
    SUCCESS = (By.ID, "profile-success")

    READY_ELEMENT = SAVE

    ERRORS = {
        "full_name": FULL_NAME_ERROR,
        "email": EMAIL_ERROR,
        "phone": PHONE_ERROR,
        "address": ADDRESS_ERROR,
    }

    def wait_until_loaded(self):
        super().wait_until_loaded()
        # Fields are populated client-side from storage; wait until the form is filled.
        self._wait().until(
            lambda d: d.find_element(*self.FULL_NAME).get_attribute("value"),
            "Profile form was not populated with the saved full name",
        )
        return self

    def update(self, full_name=None, email=None, phone=None, address=None) -> None:
        """Overwrite the given fields (None leaves a field untouched) and save."""
        for locator, value in (
            (self.FULL_NAME, full_name),
            (self.EMAIL, email),
            (self.PHONE, phone),
            (self.ADDRESS, address),
        ):
            if value is not None:
                self.type(locator, value)
        self.click(self.SAVE)

    def values(self) -> dict:
        return {
            "username": self.value_of(self.USERNAME) or self.text_of(self.USERNAME),
            "full_name": self.value_of(self.FULL_NAME),
            "email": self.value_of(self.EMAIL),
            "phone": self.value_of(self.PHONE),
            "address": self.value_of(self.ADDRESS),
        }

    def success_text(self, expected: str) -> str:
        return self.wait_text_equals(self.SUCCESS, expected)

    def error_text(self, field: str, expected: str | None = None) -> str:
        locator = self.ERRORS[field]
        if expected is not None:
            return self.wait_text_equals(locator, expected)
        self.wait_visible(locator)
        return self.text_of(locator)

    def is_success_shown(self) -> bool:
        return self.is_visible(self.SUCCESS)
