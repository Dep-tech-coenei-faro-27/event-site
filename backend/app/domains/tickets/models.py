from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domains.payments.models import TicketTier


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "qr_payload IS NULL OR length(trim(qr_payload)) > 0",
            name="ck_tickets_qr_payload_not_blank",
        ),
        # Um bilhete por pessoa: só pode existir uma linha activa por utilizador. O
        # índice é parcial para que cancelar um bilhete liberte o lugar.
        Index(
            "uq_tickets_user_id_active",
            "user_id",
            unique=True,
            postgresql_where=text("payment_status <> 'cancelled'"),
            sqlite_where=text("payment_status <> 'cancelled'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    transaction_reference: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    # The modality bought, as a value and not a foreign key: inserting a ticket must
    # not lock the modality row that a late payment locks to check the stock.
    ticket_tier: Mapped[TicketTier | None] = mapped_column(
        SAEnum(
            TicketTier,
            name="ck_tickets_ticket_tier",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=20,
        ),
        nullable=True,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="ck_tickets_payment_status",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )
    qr_payload: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
