"""Exact user-facing messages, copied verbatim from testing/APP_CONTRACT.md §3."""

# Login
USERNAME_REQUIRED = "Username is required."
PASSWORD_REQUIRED = "Password is required."
INVALID_CREDENTIALS = "Invalid username or password."
ACCOUNT_LOCKED = "Your account has been locked. Please contact support."
LOGGED_OUT = "You have been logged out."
AUTH_REQUIRED = "Please sign in to continue."

# Register / profile
FULL_NAME_REQUIRED = "Full name is required."
EMAIL_REQUIRED = "Email is required."
EMAIL_INVALID = "Enter a valid email address."
EMAIL_DUPLICATE = "An account already exists with this email."
REGISTER_PASSWORD_REQUIRED = "Password is required."
PASSWORD_TOO_SHORT = "Password must be at least 8 characters."
PASSWORD_NEEDS_LETTER_AND_NUMBER = "Password must contain at least one letter and one number."
INITIAL_DEPOSIT_REQUIRED = "Initial deposit is required."
ACCOUNT_CREATED = "Account created successfully"
PHONE_REQUIRED = "Phone number is required."
PROFILE_UPDATED = "Profile updated successfully."

# Transfer
FROM_ACCOUNT_REQUIRED = "Select the account to transfer from."
TO_ACCOUNT_REQUIRED = "Recipient account number is required."
RECIPIENT_NOT_FOUND = "Recipient account not found."
SAME_ACCOUNT = "You cannot transfer to the same account."
AMOUNT_REQUIRED = "Amount is required."
AMOUNT_NOT_POSITIVE = "Amount must be greater than zero."
AMOUNT_INVALID = "Enter a valid amount."
INSUFFICIENT_BALANCE = "Insufficient balance."
TRANSFER_LIMIT = "Transfers are limited to $10,000.00 per transaction."
ACCOUNTS_FROZEN = "Your accounts are frozen. Transfers are disabled — please contact support."
TRANSFER_SUCCESS = "Transfer successful"
TRANSFER_CATEGORY = "Transfer"

# Change password
CURRENT_PASSWORD_REQUIRED = "Current password is required."
CURRENT_PASSWORD_INCORRECT = "Current password is incorrect."
NEW_PASSWORD_REQUIRED = "New password is required."
NEW_PASSWORD_SAME_AS_CURRENT = "New password must be different from the current password."
CONFIRM_PASSWORD_REQUIRED = "Please confirm the new password."
PASSWORDS_DO_NOT_MATCH = "Passwords do not match."
PASSWORD_CHANGED = "Password changed successfully."

# Not found
PAGE_NOT_FOUND = "Page not found"
