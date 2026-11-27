"""Discount codes: a percentage off the price in force, for non-student tickets.

The codes live here, in the code, not in the database: there is one today and it has
no limit of uses and no end date (decided with the organisation). Adding or removing a
code is a change to this file. The price is always worked out on the server: the
checkout only shows what the server says and sends it back as ``expected_price_cents``.
"""

# code (upper case, no spaces) -> percentage off
DISCOUNT_CODES: dict[str, int] = {"ALGARVEEVOLUTION": 10}


def normalize_discount_code(value: str | None) -> str | None:
    """The code as compared: no spaces, upper case; ``None`` if nothing is left."""
    if value is None:
        return None
    cleaned = "".join(value.split())
    if not cleaned:
        return None
    # Only plain ASCII is folded to upper case: ``str.upper`` also turns letters like
    # the dotless i or the long s into I and S, which would make a code that is not
    # the one we gave match. Anything else is kept as typed and never matches.
    return cleaned.upper() if cleaned.isascii() else cleaned


def discount_percent(code: str) -> int | None:
    """The percentage off for a (normalised) code, or ``None`` if it does not exist."""
    return DISCOUNT_CODES.get(code)


def price_with_discount(price_cents: int, percent: int) -> int:
    """The price after the discount, rounded to the nearest cent (half up)."""
    return price_cents - (price_cents * percent + 50) // 100
