from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password
from app.core.validators import AsciiEmail, validate_name
from app.domains.users.enums import Course, PortugueseInstitution, Role
from app.domains.users.models import StudentVerificationStatus


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: AsciiEmail
    password: str = Field(min_length=8, max_length=200)
    accept_terms: bool
    institution: PortugueseInstitution | None = None
    course: Course | None = None

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
    institution: PortugueseInstitution | None = None
    course: Course | None = None


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
    institution: PortugueseInstitution | None = None
    course: Course | None = None

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_name(value)
