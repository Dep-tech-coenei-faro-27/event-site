from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EmailOutbox(Base):
    """An email waiting to be sent, or the record that it was."""

    __tablename__ = "email_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')", name="ck_email_outbox_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    to_email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(255))
    # Emptied once the email is sent: it can hold links that sign someone in.
    html_body: Mapped[str] = mapped_column(Text)
    # An optional key that stops the same email being queued twice.
    dedupe_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    status: Mapped[EmailStatus] = mapped_column(
        String(10), default=EmailStatus.PENDING, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Never holds the recipient: only the kind of error and a short message.
    last_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
