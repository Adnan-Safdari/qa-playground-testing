"""Module: Money Transfer (SB-TR-*).

Business rules are verified through `data-cents` attributes (integer cents), not just
the formatted text: sender −amount, recipient +amount, combined total unchanged, and two
transaction rows sharing one reference.
"""

import pytest

from pages import AccountsPage, TransactionsPage, TransferPage
from test_data import customers, transfers
from test_data import messages as msg
from test_data.users import FROZEN_USER, STANDARD_USER
from utils.money import format_cents

pytestmark = pytest.mark.transfer

STD_CHECKING, STD_SAVINGS = list(STANDARD_USER.accounts)


@pytest.fixture
def funded_pair(register_customer):
    """Acc-A and Acc-B, each opened through registration with $5,000.00 (both logged out)."""
    sender, recipient = customers.sender("5000"), customers.recipient("5000")
    sender_account = register_customer(sender)
    recipient_account = register_customer(recipient)
    return sender, sender_account, recipient, recipient_account


@pytest.fixture
def standard_transfer_page(login_as, driver, base_url) -> TransferPage:
    login_as(STANDARD_USER.username, STANDARD_USER.password)
    return TransferPage(driver, base_url).open()


def _transfer_500(login_as, driver, base_url, sender, sender_account, recipient_account):
    login_as(sender.username, sender.password)
    page = TransferPage(driver, base_url).open()
    page.select_from_account(sender_account)
    assert page.available_balance_cents(transfers.OPENING_BALANCE_CENTS) == transfers.OPENING_BALANCE_CENTS
    page.transfer(sender_account, recipient_account, transfers.TRANSFER_AMOUNT)
    return page, page.wait_for_receipt()


@pytest.mark.testcase("SB-TR-01")
def test_successful_transfer(funded_pair, login_as, driver, base_url):
    sender, sender_account, recipient, recipient_account = funded_pair
    expected_sender = transfers.OPENING_BALANCE_CENTS - transfers.TRANSFER_AMOUNT_CENTS
    expected_recipient = transfers.OPENING_BALANCE_CENTS + transfers.TRANSFER_AMOUNT_CENTS

    page, receipt = _transfer_500(login_as, driver, base_url, sender, sender_account, recipient_account)

    assert msg.TRANSFER_SUCCESS in receipt.message
    assert receipt.reference, "Transfer reference is empty"
    assert transfers.TRANSFER_AMOUNT_TEXT in receipt.amount_text
    assert sender_account[-4:] in receipt.from_account
    assert recipient_account[-4:] in receipt.to_account
    assert receipt.new_balance_cents == expected_sender
    assert receipt.new_balance_text == format_cents(expected_sender)

    # Sender's balance on the accounts page.
    accounts = AccountsPage(driver, base_url).open()
    sender_balance = accounts.account(sender_account)
    assert sender_balance.balance_cents == expected_sender
    assert sender_balance.balance_text == format_cents(expected_sender)  # $4,500.00
    accounts.logout()

    # Recipient's balance, seen by the recipient.
    login_as(recipient.username, recipient.password)
    recipient_balance = AccountsPage(driver, base_url).open().account(recipient_account)
    assert recipient_balance.balance_cents == expected_recipient
    assert recipient_balance.balance_text == format_cents(expected_recipient)  # $5,500.00

    # Money is neither created nor destroyed.
    assert sender_balance.balance_cents + recipient_balance.balance_cents == 2 * transfers.OPENING_BALANCE_CENTS


@pytest.mark.testcase("SB-TR-02")
def test_insufficient_balance(register_customer, driver, base_url):
    sender = customers.sender(transfers.LOW_BALANCE_DEPOSIT)
    sender_account = register_customer(sender, logout=False)  # stays logged in as Acc-A

    page = TransferPage(driver, base_url).open()
    page.transfer(sender_account, transfers.EXTERNAL_RECIPIENT, transfers.OVERDRAW_AMOUNT)

    assert page.error_text("amount", msg.INSUFFICIENT_BALANCE) == msg.INSUFFICIENT_BALANCE
    assert not page.is_success_shown()
    assert page.available_balance_cents() == transfers.LOW_BALANCE_CENTS

    account = AccountsPage(driver, base_url).open().account(sender_account)
    assert account.balance_cents == transfers.LOW_BALANCE_CENTS


@pytest.mark.testcase("SB-TR-03")
def test_invalid_recipient_account(standard_transfer_page, driver, base_url):
    page = standard_transfer_page
    for recipient in transfers.INVALID_RECIPIENTS:
        page.transfer(STD_CHECKING, recipient, transfers.SMALL_AMOUNT)
        actual = page.error_text("to_account", msg.RECIPIENT_NOT_FOUND)
        assert actual == msg.RECIPIENT_NOT_FOUND, f"recipient {recipient!r}: {actual!r}"
        assert not page.is_success_shown()

    balance = AccountsPage(driver, base_url).open().balance_cents(STD_CHECKING)
    assert balance == STANDARD_USER.accounts[STD_CHECKING]


@pytest.mark.testcase("SB-TR-04")
def test_zero_amount_rejected(standard_transfer_page):
    page = standard_transfer_page
    page.transfer(STD_CHECKING, STD_SAVINGS, transfers.ZERO_AMOUNT)

    assert page.error_text("amount", msg.AMOUNT_NOT_POSITIVE) == msg.AMOUNT_NOT_POSITIVE
    assert not page.is_success_shown()
    assert page.available_balance_cents() == STANDARD_USER.accounts[STD_CHECKING]


@pytest.mark.testcase("SB-TR-05")
def test_negative_amount_rejected(standard_transfer_page):
    page = standard_transfer_page
    page.transfer(STD_CHECKING, STD_SAVINGS, transfers.NEGATIVE_AMOUNT)

    assert page.error_text("amount", msg.AMOUNT_INVALID) == msg.AMOUNT_INVALID
    assert not page.is_success_shown()
    assert page.available_balance_cents() == STANDARD_USER.accounts[STD_CHECKING]


@pytest.mark.testcase("SB-TR-06")
def test_mandatory_fields_blank(standard_transfer_page):
    page = standard_transfer_page
    assert page.selected_value(TransferPage.FROM_ACCOUNT) == "", "From-account should start unselected"
    page.submit()

    expected = {
        "from_account": msg.FROM_ACCOUNT_REQUIRED,
        "to_account": msg.TO_ACCOUNT_REQUIRED,
        "amount": msg.AMOUNT_REQUIRED,
    }
    actual = {field: page.error_text(field, text) for field, text in expected.items()}
    assert actual == expected
    assert not page.is_success_shown()


@pytest.mark.testcase("SB-TR-07")
def test_transaction_history_updated(funded_pair, login_as, driver, base_url):
    sender, sender_account, recipient, recipient_account = funded_pair
    _, receipt = _transfer_500(login_as, driver, base_url, sender, sender_account, recipient_account)

    # Sender side: newest row is the debit.
    history = TransactionsPage(driver, base_url).open()
    debit = history.newest()
    assert debit.reference == receipt.reference
    assert debit.account == sender_account
    assert debit.description == f"Transfer to {recipient_account}"
    assert debit.category == msg.TRANSFER_CATEGORY
    assert debit.amount_cents == -transfers.TRANSFER_AMOUNT_CENTS
    assert debit.amount_text == format_cents(-transfers.TRANSFER_AMOUNT_CENTS)  # -$500.00
    history.logout()

    # Recipient side: matching credit with the same reference.
    login_as(recipient.username, recipient.password)
    credit = TransactionsPage(driver, base_url).open().newest()
    assert credit.reference == receipt.reference
    assert credit.account == recipient_account
    assert credit.description == f"Transfer from {sender_account}"
    assert credit.category == msg.TRANSFER_CATEGORY
    assert credit.amount_cents == transfers.TRANSFER_AMOUNT_CENTS
    assert format_cents(transfers.TRANSFER_AMOUNT_CENTS) in credit.amount_text


@pytest.mark.testcase("SB-TR-08")
def test_frozen_user_transfer_rejected(login_as, driver, base_url):
    from_account = list(FROZEN_USER.accounts)[0]
    login_as(FROZEN_USER.username, FROZEN_USER.password)
    page = TransferPage(driver, base_url).open()
    assert page.is_visible(TransferPage.FROZEN_NOTICE), "Frozen-account notice is not shown"

    page.transfer(from_account, transfers.EXTERNAL_RECIPIENT, transfers.SMALL_AMOUNT)

    assert page.error_text("form", msg.ACCOUNTS_FROZEN) == msg.ACCOUNTS_FROZEN
    assert not page.is_success_shown()
    assert page.available_balance_cents() == FROZEN_USER.accounts[from_account]
