import re
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.domains.payments.discounts import normalize_discount_code
from app.domains.payments.models import ShirtSize, TicketTier, TransactionStatus

_PORTUGUESE_MOBILE = re.compile(r"9\d{8}")


def normalize_phone(value: str) -> str:
    """Reduce a Portuguese mobile number to ``9XXXXXXXX``.

    Accepts spaces, ``+351``/``00351`` prefixes and separators so the browser can
    send whatever the user typed.
    """
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00351"):
        digits = digits[5:]
    elif digits.startswith("351") and len(digits) > 9:
        digits = digits[3:]
    if not _PORTUGUESE_MOBILE.fullmatch(digits):
        raise ValueError("phone must be a Portuguese mobile number, e.g. 912345678")
    return digits


# Leading digits the tax authority assigns (a leading 0 never exists; 4 only as 45).
_NIF_FIRST_DIGIT = re.compile(r"[1235-9]|45")


def normalize_nif(value: str | None) -> str | None:
    """Return a Portuguese NIF as nine ASCII digits, or ``None`` when it was left empty.

    Accepts spaces, dots, hyphens and a ``PT`` prefix. The NIF is optional, so an
    empty value is fine; a filled one must have nine digits (0-9 only: other scripts'
    digits are refused), a leading digit that exists and a valid check digit (mod 11).
    """
    if value is None or not value.strip():
        return None
    digits = re.sub(r"[\s.-]", "", re.sub(r"^\s*PT", "", value, flags=re.IGNORECASE))
    if not re.fullmatch(r"[0-9]{9}", digits):
        raise ValueError("nif must have 9 digits")
    if not _NIF_FIRST_DIGIT.match(digits):
        raise ValueError("nif does not start with a valid digit")
    total = sum(int(d) * (9 - i) for i, d in enumerate(digits[:8]))
    remainder = total % 11
    check = 0 if remainder < 2 else 11 - remainder
    if check != int(digits[8]):
        raise ValueError("nif check digit is not valid")
    return digits


_POSTAL_CODE = re.compile(r"[0-9]{4}[- ]?[0-9]{3}")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _clean_text(
    value: str | None, *, minimum: int, maximum: int, what: str
) -> str | None:
    """Tidy an address line (spaces, control characters, a leading formula sign).

    ``None`` when it was left empty.
    """
    if value is None:
        return None
    # A cell that starts with = + - or @ runs as a formula when the treasurer opens the
    # export in a spreadsheet: no real street or city starts like that, so drop them.
    text = " ".join(_CONTROL_CHARS.sub(" ", value).split()).lstrip("=+-@ ")
    if not text:
        return None
    if not minimum <= len(text) <= maximum:
        raise ValueError(f"{what} must have {minimum} to {maximum} characters")
    return text


def normalize_postal_code(value: str | None) -> str | None:
    """Return a Portuguese postal code as ``NNNN-NNN`` (``8000 123`` is fine too)."""
    if value is None or not value.strip():
        return None
    code = value.strip()
    if not _POSTAL_CODE.fullmatch(code):
        raise ValueError("postal code must look like 8005-139")
    return f"{code[:4]}-{code[-3:]}"


class PaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticket_tier: TicketTier
    phone: str
    email: EmailStr | None = None
    # The longest accepted spelling is "PT 123 456 789"; the cap only bounds the work.
    nif: str | None = Field(default=None, max_length=32)
    # The address for the invoice: required with a NIF (the invoice needs it), and
    # dropped without one so no address is kept for nothing. Portugal only.
    billing_street: str | None = Field(default=None, max_length=300)
    billing_postal_code: str | None = Field(default=None, max_length=16)
    billing_city: str | None = Field(default=None, max_length=200)
    # A discount code (checked on the server; unknown or student -> 422). It is
    # compared exactly as sent: no trimming and no case folding.
    discount_code: str | None = Field(default=None, max_length=64)
    # The shirt size, required for the student modalities (they get a shirt) and
    # refused for the others. XS, S, M, L, XL or XXL, exactly as written.
    shirt_size: ShirtSize | None = None
    # One ticket per person: the field stays for compatibility but only accepts 1.
    quantity: Literal[1] = 1
    # The price (cents) the buyer was shown for one ticket. When it is sent and the
    # price in force is another one (the early bird just ended), the payment is
    # refused with 409 so nobody is charged more, or less, than what they saw.
    # Optional: a client that does not send it is charged the price in force.
    expected_price_cents: int | None = Field(default=None, gt=0)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("nif")
    @classmethod
    def validate_nif(cls, value: str | None) -> str | None:
        return normalize_nif(value)

    @field_validator("discount_code")
    @classmethod
    def validate_discount_code(cls, value: str | None) -> str | None:
        return normalize_discount_code(value)

    @field_validator("billing_street")
    @classmethod
    def validate_billing_street(cls, value: str | None) -> str | None:
        return _clean_text(value, minimum=5, maximum=200, what="street")

    @field_validator("billing_postal_code")
    @classmethod
    def validate_billing_postal_code(cls, value: str | None) -> str | None:
        return normalize_postal_code(value)

    @field_validator("billing_city")
    @classmethod
    def validate_billing_city(cls, value: str | None) -> str | None:
        return _clean_text(value, minimum=2, maximum=100, what="city")

    @model_validator(mode="after")
    def address_goes_with_the_nif(self) -> "PaymentInitiateRequest":
        address = (self.billing_street, self.billing_postal_code, self.billing_city)
        if self.nif is None:
            self.billing_street = self.billing_postal_code = self.billing_city = None
        elif not all(address):
            raise ValueError("billing address is required with a nif")
        return self


class TransactionRead(BaseModel):
    reference: str
    ticket_tier: TicketTier
    status: TransactionStatus
    amount_cents: int
    quantity: int
    currency: str = "EUR"
    phone: str
    expires_at: datetime
    confirmed_at: datetime | None = None
    created_at: datetime


class TicketTierRead(BaseModel):
    """A modality as the checkout shows it: price and whether it can be bought now.

    The number of seats left is not exposed, only whether there are any.
    """

    tier: TicketTier
    name: str
    price_cents: int | None
    # The regular price, only while price_cents is an early-bird price (above it).
    normal_price_cents: int | None = None
    currency: str = "EUR"
    is_student: bool
    sale_open: bool
    available: bool
    # When the ticket office opens, only while it has not opened yet (SALES_OPEN_AT).
    opens_at: datetime | None = None


class DiscountCheckRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticket_tier: TicketTier
    code: str = Field(max_length=64)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return value


class DiscountCheckRead(BaseModel):
    """What the checkout shows for a valid code: the price the server will charge."""

    code: str
    percent: int
    price_cents: int
    currency: str = "EUR"


class ShirtSizeUpdate(BaseModel):
    """The new size of the shirt, from the account page."""

    model_config = ConfigDict(extra="forbid")

    shirt_size: ShirtSize
