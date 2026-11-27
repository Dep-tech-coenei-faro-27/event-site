"""Discount codes: a percentage off the price in force, for non-student tickets.

The codes live here, in the code, not in the database: there is one today and it has
no limit of uses and no end date (decided with the organisation). Adding or removing a
code is a change to this file. The price is always worked out on the server: the
checkout only shows what the server says and sends it back as ``expected_price_cents``.
"""

# The code exactly as it must be typed: upper case, no spaces. The comparison is exact
# (no trimming, no case folding, no Unicode folding): anything else is not the code.
DISCOUNT_CODES: dict[str, int] = {"ALGARVEEVOLUTION": 10}


def normalize_discount_code(value: str | None) -> str | None:
    """The code as sent; ``None`` only when there is no code at all (``None`` or "").

    Nothing is cleaned up: spaces, lower case or look-alike letters make a different
    text, which is not in ``DISCOUNT_CODES`` and is refused.
    """
    return value or None


def discount_percent(code: str) -> int | None:
    """The percentage off for the code exactly as sent, or ``None`` if unknown."""
    return DISCOUNT_CODES.get(code)


def price_with_discount(price_cents: int, percent: int) -> int:
    """The price after the discount, rounded to the nearest cent (half up)."""
    return price_cents - (price_cents * percent + 50) // 100
