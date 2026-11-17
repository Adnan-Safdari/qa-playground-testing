"""Module: Create New Account (SB-AC-*) — public registration at /bank/register."""

import re

import pytest

from pages import AccountsPage, RegisterPage
from test_data import customers
from test_data import messages as msg
from utils.money import format_cents

pytestmark = pytest.mark.create_account


@pytest.fixture
def register_page(driver, base_url) -> RegisterPage:
    return RegisterPage(driver, base_url).open()


@pytest.mark.testcase("SB-AC-01")
def test_create_account_with_valid_details(register_page, driver, base_url):
    rahul = customers.RAHUL
    register_page.register(rahul.full_name, rahul.email, rahul.password, rahul.initial_deposit)

    confirmation = register_page.wait_for_success()
    assert msg.ACCOUNT_CREATED in confirmation
    account_number = register_page.new_account_number
    assert re.fullmatch(r"\d{10}", account_number), f"Unexpected account number {account_number!r}"
    assert register_page.new_account_balance == format_cents(customers.RAHUL_EXPECTED_BALANCE_CENTS)

    # The customer is logged in and the account exists with the deposited balance.
    accounts = AccountsPage(driver, base_url).open()
    assert accounts.current_username == rahul.username
    account = accounts.account(account_number)
    assert account.number == account_number
    assert account.nickname == customers.NEW_ACCOUNT_NICKNAME
    assert account.balance_cents == customers.RAHUL_EXPECTED_BALANCE_CENTS
    assert account.balance_text == format_cents(customers.RAHUL_EXPECTED_BALANCE_CENTS)


@pytest.mark.testcase("SB-AC-02")
def test_mandatory_field_validation(register_page):
    register_page.submit()

    expected = {
        "full_name": msg.FULL_NAME_REQUIRED,
        "email": msg.EMAIL_REQUIRED,
        "password": msg.REGISTER_PASSWORD_REQUIRED,
        "initial_deposit": msg.INITIAL_DEPOSIT_REQUIRED,
    }
    actual = {field: register_page.error_text(field, text) for field, text in expected.items()}
    assert actual == expected
    assert not register_page.is_visible(RegisterPage.REGISTER_SUCCESS)


@pytest.mark.testcase("SB-AC-03")
def test_invalid_email_format(register_page):
    rahul = customers.RAHUL
    register_page.register(rahul.full_name, customers.INVALID_EMAIL, rahul.password, rahul.initial_deposit)

    assert register_page.error_text("email", msg.EMAIL_INVALID) == msg.EMAIL_INVALID
    assert not register_page.is_visible(RegisterPage.REGISTER_SUCCESS)


@pytest.mark.testcase("SB-AC-04")
def test_weak_password_rejected(register_page):
    rahul = customers.RAHUL
    register_page.register(rahul.full_name, rahul.email, customers.WEAK_PASSWORD, rahul.initial_deposit)

    assert register_page.error_text("password", msg.PASSWORD_TOO_SHORT) == msg.PASSWORD_TOO_SHORT
    assert not register_page.is_visible(RegisterPage.REGISTER_SUCCESS)


@pytest.mark.testcase("SB-AC-05")
def test_duplicate_account_rejected(register_customer, driver, base_url):
    rahul = customers.RAHUL
    register_customer(rahul)  # registers, then logs out

    page = RegisterPage(driver, base_url).open()
    page.register(rahul.full_name, rahul.email, rahul.password, rahul.initial_deposit)

    assert page.error_text("email", msg.EMAIL_DUPLICATE) == msg.EMAIL_DUPLICATE
    assert not page.is_visible(RegisterPage.REGISTER_SUCCESS)
