from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db.base import Base
from app.domains.users.enums import Role


class StudentVerificationStatus(StrEnum):
    """Whether an account proved it is entitled to the student price."""

    NONE = "none"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"


# Before the proof of enrolment, an account without proof was stored as "pending".
# Rows and the previous code (which keeps serving during a deploy) still use it, so
# it is read as NONE and a later migration can rewrite it.
LEGACY_NONE = "pending"
STUDENT_STATUS_VALUES = (
    LEGACY_NONE,
    *(status.value for status in StudentVerificationStatus),
)


class StudentStatusType(TypeDecorator):
    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else StudentVerificationStatus(value).value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value == LEGACY_NONE:
            return StudentVerificationStatus.NONE
        return StudentVerificationStatus(value)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_users_name_not_blank"),
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_blank"),
        CheckConstraint(
            "length(password_hash) > 0", name="ck_users_password_hash_not_empty"
        ),
        CheckConstraint(
            "student_verification_status IN ("
            + ", ".join(f"'{value}'" for value in STUDENT_STATUS_VALUES)
            + ")",
            name="ck_users_student_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        SAEnum(
            Role,
            name="ck_users_role",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=Role.USER,
        server_default=Role.USER.name,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    student_verification_status: Mapped[StudentVerificationStatus] = mapped_column(
        StudentStatusType(),
        default=StudentVerificationStatus.NONE,
        nullable=False,
        server_default=StudentVerificationStatus.NONE.value,
    )
    student_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        server_default="0",
    )
    terms_accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    term_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=False,
        server_default="'1.0'",
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Contacto opcional da pessoa (o telemóvel do pagamento fica na transação).
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)


Index("uq_users_email_lower", func.lower(User.email), unique=True)
