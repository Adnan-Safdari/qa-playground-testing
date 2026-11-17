"""Money formatting that mirrors the app's display format (en-US, USD)."""


def format_cents(cents: int) -> str:
    """1245000 -> '$12,450.00'; -50000 -> '-$500.00'."""
    sign = "-" if cents < 0 else ""
    dollars, rem = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rem:02d}"
