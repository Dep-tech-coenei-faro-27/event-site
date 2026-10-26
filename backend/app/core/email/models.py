from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
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
    # The plain-text twin of ``html_body`` (``multipart/alternative``); null means the
    # sender derives one from the HTML. Emptied once sent, like the HTML.
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Content-ID -> base64 PNG shown inline (the ticket QR). Emptied once sent too.
    inline_images: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
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


class EmailTransportUsage(Base):
    """How many emails a transport sent on one UTC day, shared by every worker.

    ``exhausted_at`` is set when the provider refused for its daily quota: the
    transport is then skipped until the next UTC day, which has a new row.
    """

    __tablename__ = "email_transport_usage"

    transport: Mapped[str] = mapped_column(String(20), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    exhausted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
