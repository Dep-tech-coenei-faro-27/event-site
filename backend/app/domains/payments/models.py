from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TicketTier(StrEnum):
    """The ticket modalities sold for the event."""

    ACESSO = "acesso"
    REFEICOES = "refeicoes"
    COMPLETO = "completo"
    GERAL = "geral"


class TransactionStatus(StrEnum):
    """Lifecycle of a payment. Pending ones expire after the MB WAY window."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_tickets_price_not_negative"),
        CheckConstraint(
            "inventory_limit IS NULL OR inventory_limit >= 0",
            name="ck_tickets_inventory_not_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tier: Mapped[TicketTier] = mapped_column(
        SAEnum(
            TicketTier,
            name="ck_tickets_tier",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=20,
        ),
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    price_cents: Mapped[int] = mapped_column(Integer)
    is_student: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    inventory_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
        CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="RESTRICT"), index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, server_default="1"
    )
    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(
            TransactionStatus,
            name="ck_transactions_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=20,
        ),
        default=TransactionStatus.PENDING,
        nullable=False,
        server_default=TransactionStatus.PENDING.value,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(30))
    provider_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
