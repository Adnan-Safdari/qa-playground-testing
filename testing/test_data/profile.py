"""Profile and password-change data."""

from test_data.customers import unique_email

UPDATED_PROFILE = {
    "full_name": "Alexandra Morgan-Reed",
    "email": unique_email("alex.updated"),
    "phone": "5550198765",
    "address": "221B Baker Street, Springfield",
}
INVALID_EMAIL = "alex@invalid"

NEW_PASSWORD = "NewSauce2026"
MISMATCHED_CONFIRMATION = "NewSauce2027"
WEAK_NEW_PASSWORD = "abc"
