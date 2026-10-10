import re
from datetime import datetime

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


class PaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticket_tier: TicketTier
    phone: str
    email: EmailStr | None = None
    quantity: int = Field(default=1, ge=1, le=10)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)


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
