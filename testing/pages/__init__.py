"""SecureBank Page Object Model. Every selector used by the suite lives in this package."""

from pages.accounts_page import AccountCard, AccountsPage
from pages.app_page import AppPage
from pages.base_page import BasePage
from pages.change_password_page import ChangePasswordPage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.not_found_page import NotFoundPage
from pages.profile_page import ProfilePage
from pages.register_page import RegisterPage
from pages.transactions_page import TransactionRow, TransactionsPage
from pages.transfer_page import TransferPage, TransferReceipt

__all__ = [
    "AccountCard", "AccountsPage", "AppPage", "BasePage", "ChangePasswordPage",
    "DashboardPage", "LoginPage", "NotFoundPage", "ProfilePage", "RegisterPage",
    "TransactionRow", "TransactionsPage", "TransferPage", "TransferReceipt",
]
