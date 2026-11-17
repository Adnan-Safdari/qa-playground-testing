"""Dashboard — /bank/dashboard."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.app_page import AppPage


class DashboardPage(AppPage):
    PATH = "/bank/dashboard"
    TITLE = "Dashboard | SecureBank"

    STAT_NET_WORTH = (By.ID, "stat-net-worth")
    STAT_NET_CHANGE = (By.ID, "stat-net-change")
    STAT_INCOME = (By.ID, "stat-income")
    STAT_EXPENSES = (By.ID, "stat-expenses")
    STAT_ACCOUNT_COUNT = (By.ID, "stat-account-count")

    QA_OPEN_ACCOUNT = (By.ID, "qa-open-account")
    QA_TRANSFER = (By.ID, "qa-transfer")
    QA_TRANSACTIONS = (By.ID, "qa-transactions")
    QA_PROFILE = (By.ID, "qa-profile")
    QA_CHANGE_PASSWORD = (By.ID, "qa-change-password")

    RECENT_TRANSACTIONS = (By.ID, "recent-transactions")
    RECENT_TRANSACTION_ROWS = (By.CSS_SELECTOR, '[data-testid="recent-transaction-row"]')
    VIEW_ALL_TRANSACTIONS = (By.ID, "view-all-transactions")

    @property
    def account_count_text(self) -> str:
        return self.text_of(self.STAT_ACCOUNT_COUNT)

    @property
    def net_worth_cents(self) -> int:
        return self.cents_of(self.STAT_NET_WORTH)
