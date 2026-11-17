"""Registration (new customer) data.

Each test runs in a fresh browser profile, so fixed data such as the brief's
`rahul.demo1@test.com` is safe. Generated customers still get a per-run suffix so the
values in reports are traceable and never collide inside one browser.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

RUN_SUFFIX = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + secrets.token_hex(2)


@dataclass(frozen=True)
class Customer:
    full_name: str
    email: str
    password: str
    initial_deposit: str

    @property
    def username(self) -> str:
        """Registered users log in with their (lower-cased) email."""
        return self.email.lower()


def unique_email(prefix: str) -> str:
    return f"{prefix}.{RUN_SUFFIX}@test.com"


# SB-AC-01 / SB-AC-05 — fixed values from the hackathon test plan.
RAHUL = Customer("Rahul Kumar", "rahul.demo1@test.com", "Test@123", "1000")
RAHUL_EXPECTED_BALANCE_CENTS = 100_000
NEW_ACCOUNT_NICKNAME = "Everyday Checking"

INVALID_EMAIL = "rahul@invalid"
WEAK_PASSWORD = "123"


def sender(initial_deposit: str = "5000") -> Customer:
    """Acc-A in the transfer scenarios."""
    return Customer("Asha Sender", unique_email("qa.sender"), "Sender@123", initial_deposit)


def recipient(initial_deposit: str = "5000") -> Customer:
    """Acc-B in the transfer scenarios."""
    return Customer("Bala Recipient", unique_email("qa.recipient"), "Recipient@123", initial_deposit)
