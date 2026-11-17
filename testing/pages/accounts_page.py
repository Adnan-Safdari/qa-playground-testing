"""Accounts list — /bank/accounts."""

from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.common.by import By

from pages.app_page import AppPage


@dataclass(frozen=True)
class AccountCard:
    number: str
    nickname: str
    account_type: str
    balance_text: str
    balance_cents: int


class AccountsPage(AppPage):
    PATH = "/bank/accounts"
    TITLE = "Accounts | SecureBank"

    OPEN_ACCOUNT_BUTTON = (By.ID, "open-account-button")
    ACCOUNT_CARDS = (By.CSS_SELECTOR, '[data-testid="account-card"]')

    # Children of an account card (searched relative to the card element).
    CARD_NICKNAME = (By.CSS_SELECTOR, '[data-testid="account-nickname"]')
    CARD_TYPE = (By.CSS_SELECTOR, '[data-testid="account-type"]')
    CARD_NUMBER = (By.CSS_SELECTOR, '[data-testid="account-number"]')
    CARD_BALANCE = (By.CSS_SELECTOR, '[data-testid="account-balance"]')

    @staticmethod
    def card_locator(account_number: str):
        return (
            By.CSS_SELECTOR,
            f'[data-testid="account-card"][data-account-number="{account_number}"]',
        )

    def account(self, account_number: str) -> AccountCard:
        card = self.wait_visible(self.card_locator(account_number))
        balance = card.find_element(*self.CARD_BALANCE)
        return AccountCard(
            number=card.find_element(*self.CARD_NUMBER).text.strip(),
            nickname=card.find_element(*self.CARD_NICKNAME).text.strip(),
            account_type=card.find_element(*self.CARD_TYPE).text.strip(),
            balance_text=balance.text.strip(),
            balance_cents=int(balance.get_attribute("data-cents")),
        )

    def account_numbers(self) -> list[str]:
        cards = self.wait_all_visible(self.ACCOUNT_CARDS)
        return [c.get_attribute("data-account-number") for c in cards]

    def balance_cents(self, account_number: str) -> int:
        return self.account(account_number).balance_cents
