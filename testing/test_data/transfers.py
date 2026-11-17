"""Money-transfer scenario data (amounts in dollars as typed, cents for assertions)."""

OPENING_BALANCE_CENTS = 500_000          # $5,000.00 for Acc-A and Acc-B
TRANSFER_AMOUNT = "500"
TRANSFER_AMOUNT_CENTS = 50_000
TRANSFER_AMOUNT_TEXT = "$500.00"

LOW_BALANCE_DEPOSIT = "500"              # SB-TR-02 Acc-A opening balance
LOW_BALANCE_CENTS = 50_000
OVERDRAW_AMOUNT = "1000"

INVALID_RECIPIENTS = ["Acc-XYZ", "9999999999"]   # SB-TR-03
SMALL_AMOUNT = "100"
ZERO_AMOUNT = "0"
NEGATIVE_AMOUNT = "-100"

# Any existing customer's account can receive money; standard_user's checking.
EXTERNAL_RECIPIENT = "1002003001"
