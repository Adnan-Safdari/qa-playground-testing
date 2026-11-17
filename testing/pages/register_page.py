"""Create-account (registration) page — /bank/register."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class RegisterPage(BasePage):
    PATH = "/bank/register"
    TITLE = "Create Account | SecureBank"

    FULL_NAME = (By.ID, "full-name")
    EMAIL = (By.ID, "email")
    PASSWORD = (By.ID, "password")
    INITIAL_DEPOSIT = (By.ID, "initial-deposit")
    REGISTER_BUTTON = (By.ID, "register-button")
    LOGIN_LINK = (By.ID, "login-link")

    FULL_NAME_ERROR = (By.ID, "full-name-error")
    EMAIL_ERROR = (By.ID, "email-error")
    PASSWORD_ERROR = (By.ID, "password-error")
    INITIAL_DEPOSIT_ERROR = (By.ID, "initial-deposit-error")

    REGISTER_SUCCESS = (By.ID, "register-success")
    NEW_ACCOUNT_NUMBER = (By.ID, "new-account-number")
    NEW_ACCOUNT_BALANCE = (By.ID, "new-account-balance")
    GO_TO_DASHBOARD = (By.ID, "go-to-dashboard")

    READY_ELEMENT = REGISTER_BUTTON

    ERRORS = {
        "full_name": FULL_NAME_ERROR,
        "email": EMAIL_ERROR,
        "password": PASSWORD_ERROR,
        "initial_deposit": INITIAL_DEPOSIT_ERROR,
    }

    def fill_form(self, full_name="", email="", password="", initial_deposit="") -> None:
        self.type(self.FULL_NAME, full_name)
        self.type(self.EMAIL, email)
        self.type(self.PASSWORD, password)
        self.type(self.INITIAL_DEPOSIT, initial_deposit)

    def submit(self) -> None:
        self.click(self.REGISTER_BUTTON)

    def register(self, full_name, email, password, initial_deposit) -> None:
        self.fill_form(full_name, email, password, initial_deposit)
        self.submit()

    def wait_for_success(self) -> str:
        """Wait for the confirmation panel and return its text."""
        self.wait_visible(self.REGISTER_SUCCESS)
        self.wait_visible(self.NEW_ACCOUNT_NUMBER)
        return self.text_of(self.REGISTER_SUCCESS)

    @property
    def new_account_number(self) -> str:
        return self.text_of(self.NEW_ACCOUNT_NUMBER)

    @property
    def new_account_balance(self) -> str:
        return self.text_of(self.NEW_ACCOUNT_BALANCE)

    def error_text(self, field: str, expected: str | None = None) -> str:
        locator = self.ERRORS[field]
        if expected is not None:
            return self.wait_text_equals(locator, expected)
        self.wait_visible(locator)
        return self.text_of(locator)
