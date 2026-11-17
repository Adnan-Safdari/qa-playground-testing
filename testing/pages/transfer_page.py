"""Money transfer — /bank/transfer."""

from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.common.by import By

from pages.app_page import AppPage


@dataclass(frozen=True)
class TransferReceipt:
    reference: str
    amount_text: str
    from_account: str
    to_account: str
    new_balance_text: str
    new_balance_cents: int
    message: str


class TransferPage(AppPage):
    PATH = "/bank/transfer"
    TITLE = "Transfer | SecureBank"

    FROM_ACCOUNT = (By.ID, "from-account")
    AVAILABLE_BALANCE = (By.ID, "available-balance")
    TO_ACCOUNT = (By.ID, "to-account")
    AMOUNT = (By.ID, "amount")
    MEMO = (By.ID, "memo")
    SUBMIT = (By.ID, "transfer-submit")

    FROM_ACCOUNT_ERROR = (By.ID, "from-account-error")
    TO_ACCOUNT_ERROR = (By.ID, "to-account-error")
    AMOUNT_ERROR = (By.ID, "amount-error")
    MEMO_ERROR = (By.ID, "memo-error")
    FORM_ERROR = (By.ID, "transfer-error")
    FROZEN_NOTICE = (By.ID, "frozen-notice")

    SUCCESS = (By.ID, "transfer-success")
    REFERENCE = (By.ID, "transfer-reference")
    RECEIPT_AMOUNT = (By.ID, "transfer-amount")
    RECEIPT_FROM = (By.ID, "transfer-from-account")
    RECEIPT_TO = (By.ID, "transfer-to-account")
    RECEIPT_NEW_BALANCE = (By.ID, "transfer-new-balance")
    NEW_TRANSFER_BUTTON = (By.ID, "new-transfer-button")
    VIEW_TRANSACTIONS_LINK = (By.ID, "view-transactions-link")

    READY_ELEMENT = SUBMIT

    ERRORS = {
        "from_account": FROM_ACCOUNT_ERROR,
        "to_account": TO_ACCOUNT_ERROR,
        "amount": AMOUNT_ERROR,
        "memo": MEMO_ERROR,
        "form": FORM_ERROR,
    }

    def select_from_account(self, account_number: str) -> None:
        self.select_by_value(self.FROM_ACCOUNT, account_number)

    def from_account_options(self) -> list[str]:
        return [v for v in self.option_values(self.FROM_ACCOUNT) if v]

    def available_balance_cents(self, expected: int | None = None) -> int:
        """Balance of the selected from-account (optionally waiting for `expected`)."""
        if expected is not None:
            self.wait_attribute_equals(self.AVAILABLE_BALANCE, "data-cents", str(expected))
        else:
            self.wait_visible(self.AVAILABLE_BALANCE)
        return self.cents_of(self.AVAILABLE_BALANCE)

    def fill(self, from_account: str | None = None, to_account="", amount="", memo="") -> None:
        if from_account:
            self.select_from_account(from_account)
        self.type(self.TO_ACCOUNT, to_account)
        self.type(self.AMOUNT, amount)
        if memo:
            self.type(self.MEMO, memo)

    def submit(self) -> None:
        self.click(self.SUBMIT)

    def transfer(self, from_account: str, to_account: str, amount, memo: str = "") -> None:
        self.fill(from_account, to_account, amount, memo)
        self.submit()

    def wait_for_receipt(self) -> TransferReceipt:
        self.wait_visible(self.SUCCESS)
        self.wait_visible(self.REFERENCE)
        return TransferReceipt(
            reference=self.text_of(self.REFERENCE),
            amount_text=self.text_of(self.RECEIPT_AMOUNT),
            from_account=self.text_of(self.RECEIPT_FROM),
            to_account=self.text_of(self.RECEIPT_TO),
            new_balance_text=self.text_of(self.RECEIPT_NEW_BALANCE),
            new_balance_cents=self.cents_of(self.RECEIPT_NEW_BALANCE),
            message=self.text_of(self.SUCCESS),
        )

    def error_text(self, field: str, expected: str | None = None) -> str:
        locator = self.ERRORS[field]
        if expected is not None:
            return self.wait_text_equals(locator, expected)
        self.wait_visible(locator)
        return self.text_of(locator)

    def is_success_shown(self) -> bool:
        return self.is_visible(self.SUCCESS)
