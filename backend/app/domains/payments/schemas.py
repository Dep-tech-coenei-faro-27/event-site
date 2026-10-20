import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domains.payments.models import TicketTier, TransactionStatus

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


class PaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticket_tier: TicketTier
    phone: str
    email: EmailStr | None = None
    # The longest accepted spelling is "PT 123 456 789"; the cap only bounds the work.
    nif: str | None = Field(default=None, max_length=32)
    # One ticket per person: the field stays for compatibility but only accepts 1.
    quantity: Literal[1] = 1

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("nif")
    @classmethod
    def validate_nif(cls, value: str | None) -> str | None:
        return normalize_nif(value)


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
    currency: str = "EUR"
    is_student: bool
    sale_open: bool
    available: bool
