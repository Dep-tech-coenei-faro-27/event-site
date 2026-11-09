import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password
from app.core.validators import AsciiEmail, validate_name
from app.domains.users.enums import Role
from app.domains.users.models import StudentVerificationStatus


def normalize_contact_phone(value: str) -> str | None:
    """Número de contacto: 9 a 15 dígitos, com ou sem + e indicativo.

    Aceita espaços, pontos, hífenes e parênteses ("+351 912 345 678", "00351912345678")
    e guarda só o + opcional e os dígitos. Texto vazio quer dizer «sem contacto».
    """
    cleaned = re.sub(r"[\s.\-()]", "", value)
    if not cleaned:
        return None
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not re.fullmatch(r"\+?[0-9]{9,15}", cleaned):
        raise ValueError("phone must have 9 to 15 digits, optionally starting with +")
    return cleaned


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: AsciiEmail
    password: str = Field(min_length=8, max_length=200)
    accept_terms: bool

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("accept_terms")
    @classmethod
    def validate_accept_terms(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must accept the terms and conditions")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    is_verified: bool
    student_verification_status: StudentVerificationStatus
    phone: str | None = None


class TicketSummaryRead(BaseModel):
    """The person's active ticket, for the account page."""

    reference: str
    tier: str
    tier_name: str
    holder_name: str
    paid_at: datetime | None = None


class PendingPaymentRead(BaseModel):
    """A payment waiting for the person to approve it or for the provider to end it."""

    reference: str
    tier: str
    tier_name: str
    amount_cents: int
    expires_at: datetime


class RefundDueRead(BaseModel):
    """A payment that arrived but could not get a ticket: it will be refunded."""

    reference: str
    amount_cents: int


class UserProfileRead(UserRead):
    model_config = ConfigDict(from_attributes=True)

    qr_code: str | None = None
    ticket: TicketSummaryRead | None = None
    pending_payment: PendingPaymentRead | None = None
    refund_due: RefundDueRead | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_name(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_contact_phone(value)
