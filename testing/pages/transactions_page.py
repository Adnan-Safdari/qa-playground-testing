"""Transaction history — /bank/transactions."""

from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from pages.app_page import AppPage


@dataclass(frozen=True)
class TransactionRow:
    reference: str | None
    account_number: str | None
    date: str
    description: str
    account: str
    category: str
    amount_text: str
    amount_cents: int
    balance_text: str


class TransactionsPage(AppPage):
    PATH = "/bank/transactions"
    TITLE = "Transactions | SecureBank"

    ACCOUNT_FILTER = (By.ID, "account-filter")
    TABLE = (By.ID, "transactions-table")
    ROWS = (By.CSS_SELECTOR, '[data-testid="transaction-row"]')
    NO_TRANSACTIONS = (By.ID, "no-transactions")

    CELL_DATE = (By.CSS_SELECTOR, '[data-testid="transaction-date"]')
    CELL_DESCRIPTION = (By.CSS_SELECTOR, '[data-testid="transaction-description"]')
    CELL_ACCOUNT = (By.CSS_SELECTOR, '[data-testid="transaction-account"]')
    CELL_CATEGORY = (By.CSS_SELECTOR, '[data-testid="transaction-category"]')
    CELL_AMOUNT = (By.CSS_SELECTOR, '[data-testid="transaction-amount"]')
    CELL_BALANCE = (By.CSS_SELECTOR, '[data-testid="transaction-balance"]')

    READY_ELEMENT = ACCOUNT_FILTER

    @staticmethod
    def _parse(row: WebElement) -> TransactionRow:
        def cell(locator):
            return row.find_element(*locator)

        amount = cell(TransactionsPage.CELL_AMOUNT)
        return TransactionRow(
            reference=row.get_attribute("data-reference"),
            account_number=row.get_attribute("data-account-number"),
            date=cell(TransactionsPage.CELL_DATE).text.strip(),
            description=cell(TransactionsPage.CELL_DESCRIPTION).text.strip(),
            account=cell(TransactionsPage.CELL_ACCOUNT).text.strip(),
            category=cell(TransactionsPage.CELL_CATEGORY).text.strip(),
            amount_text=amount.text.strip(),
            amount_cents=int(amount.get_attribute("data-cents")),
            balance_text=cell(TransactionsPage.CELL_BALANCE).text.strip(),
        )

    def rows(self) -> list[TransactionRow]:
        self.wait_visible(self.TABLE)
        return [self._parse(r) for r in self.wait_all_visible(self.ROWS)]

    def newest(self) -> TransactionRow:
        return self.rows()[0]

    def rows_with_reference(self, reference: str) -> list[TransactionRow]:
        locator = (By.CSS_SELECTOR, f'[data-testid="transaction-row"][data-reference="{reference}"]')
        return [self._parse(r) for r in self.wait_all_visible(locator)]

    def filter_by_account(self, account_number: str) -> None:
        self.select_by_value(self.ACCOUNT_FILTER, account_number)
