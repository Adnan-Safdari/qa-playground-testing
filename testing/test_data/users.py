"""Seeded SecureBank users (APP_CONTRACT.md §1). All share the password `bank_sauce`."""

from dataclasses import dataclass

SEED_PASSWORD = "bank_sauce"


@dataclass(frozen=True)
class SeedUser:
    username: str
    email: str
    full_name: str
    accounts: dict  # account number -> balance in cents

    @property
    def first_name(self) -> str:
        return self.full_name.split()[0]

    @property
    def password(self) -> str:
        return SEED_PASSWORD


STANDARD_USER = SeedUser(
    "standard_user", "alex.morgan@example.com", "Alex Morgan",
    {"1002003001": 1_245_000, "1002003002": 460_000},
)
LOCKED_USER = SeedUser(
    "locked_user", "jordan.lee@example.com", "Jordan Lee",
    {"1002004001": 320_000},
)
FROZEN_USER = SeedUser(
    "frozen_user", "sam.rivera@example.com", "Sam Rivera",
    {"1002005001": 540_000, "1002005002": 210_000},
)
OVERDRAFT_USER = SeedUser(
    "overdraft_user", "casey.kim@example.com", "Casey Kim",
    {"1002006001": -25_000, "1002006002": 8_000},
)
SLOW_USER = SeedUser(
    "slow_user", "taylor.brooks@example.com", "Taylor Brooks",
    {"1002007001": 730_000, "1002007002": 150_000},
)

WRONG_PASSWORD = "wrong_sauce"
