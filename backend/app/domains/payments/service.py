import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.payments.gateway import MBWayGateway, PaymentGatewayError
from app.domains.payments.models import (
    Ticket,
    TicketTier,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import PaymentInitiateRequest, TransactionRead
from app.domains.payments.tiers import TIER_SPECS
from app.domains.users.models import StudentVerificationStatus, User

logger = logging.getLogger(__name__)

REFERENCE_PREFIX = "ENEI-"
REFERENCE_LENGTH = 15


class PaymentError(RuntimeError):
    status_code = 400


class TicketUnavailableError(PaymentError):
    status_code = 409


class TicketSoldOutError(PaymentError):
    status_code = 409


class StudentVerificationRequiredError(PaymentError):
    status_code = 403


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def generate_reference(db: Session) -> str:
    """A short, human-readable, unique payment reference (max 15 chars)."""
    for _ in range(10):
        # "ENEI-" + 10 hex chars == 15 characters, matching the UI mockup.
        reference = REFERENCE_PREFIX + secrets.token_hex(5).upper()
        if REFERENCE_LENGTH != len(reference):
            raise RuntimeError("reference length must stay at 15 characters")
        exists = db.scalar(
            select(Transaction.id).where(Transaction.reference == reference)
        )
        if exists is None:
            return reference
    raise RuntimeError("could not generate a unique payment reference")


def _reserved_quantity(db: Session, ticket: Ticket, now: datetime) -> int:
    holds = db.scalar(
        select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
            Transaction.ticket_id == ticket.id,
            (
                (Transaction.status == TransactionStatus.CONFIRMED)
                | (
                    (Transaction.status == TransactionStatus.PENDING)
                    & (Transaction.expires_at > now)
                )
            ),
        )
    )
    return int(holds or 0)


def initiate_payment(
    db: Session,
    user: User,
    payload: PaymentInitiateRequest,
    gateway: MBWayGateway,
) -> tuple[Transaction, Ticket]:
    # Lock the ticket row so that the stock check and the reservation are a single
    # atomic step. Without it, two concurrent buyers of a limited tier can both read
    # the same remaining quantity and oversell the tier.
    ticket = db.scalar(
        select(Ticket).where(Ticket.tier == payload.ticket_tier).with_for_update()
    )
    if ticket is None:
        db.rollback()
        raise TicketUnavailableError("Ticket tier is not available")

    if ticket.is_student and (
        user.student_verification_status is not StudentVerificationStatus.VERIFIED
    ):
        db.rollback()
        raise StudentVerificationRequiredError(
            "Student verification is required to buy this ticket"
        )

    now = datetime.now(UTC)
    if ticket.inventory_limit is not None:
        remaining = ticket.inventory_limit - _reserved_quantity(db, ticket, now)
        if remaining < payload.quantity:
            db.rollback()
            raise TicketSoldOutError("This ticket tier is sold out")

    amount_cents = ticket.price_cents * payload.quantity
    transaction = Transaction(
        reference=generate_reference(db),
        user_id=user.id,
        ticket_id=ticket.id,
        amount_cents=amount_cents,
        quantity=payload.quantity,
        status=TransactionStatus.PENDING,
        phone=payload.phone,
        provider=gateway.name,
        expires_at=now + timedelta(seconds=settings.MBWAY_PAYMENT_TIMEOUT_SECONDS),
    )
    db.add(transaction)
    # Persist the reservation before talking to the provider: the seat is held
    # while the user confirms, and the row lock is released without waiting on the
    # network call.
    db.commit()
    db.refresh(transaction)

    try:
        payment = gateway.create_payment(
            reference=transaction.reference,
            amount_cents=amount_cents,
            phone=payload.phone,
            email=payload.email or user.email,
        )
    except PaymentGatewayError:
        transaction.status = TransactionStatus.FAILED
        db.commit()
        raise

    transaction.provider_reference = payment.provider_reference
    db.commit()
    db.refresh(transaction)
    return transaction, ticket


def _sync_provider_status(
    db: Session, transaction: Transaction, gateway: MBWayGateway
) -> None:
    """Ask the provider for the real state of a pending payment and persist it.

    The provider is the source of truth: a confirmed payment must reach the
    frontend even if the local ``expires_at`` window already passed, and a
    failed/expired one must not stay ``pending`` until the timeout. When the
    gateway is unreachable we fall back to the local expiry window so the poll
    keeps working instead of failing the request.
    """
    now = datetime.now(UTC)
    try:
        provider_status = gateway.get_status(
            reference=transaction.reference,
            provider_reference=transaction.provider_reference,
        )
    except PaymentGatewayError:
        logger.warning(
            "MB WAY status poll failed for %s; keeping stored status",
            transaction.reference,
        )
        provider_status = TransactionStatus.PENDING

    if provider_status is TransactionStatus.PENDING:
        if _as_utc(transaction.expires_at) > now:
            return
        provider_status = TransactionStatus.EXPIRED
    elif provider_status is TransactionStatus.CONFIRMED:
        transaction.confirmed_at = now

    transaction.status = provider_status
    db.commit()
    db.refresh(transaction)


def get_transaction(
    db: Session, user: User, reference: str, gateway: MBWayGateway
) -> Transaction | None:
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.reference == reference,
            Transaction.user_id == user.id,
        )
    )
    if transaction is None:
        return None

    if transaction.status is TransactionStatus.PENDING:
        _sync_provider_status(db, transaction, gateway)

    return transaction


def ticket_tier_of(db: Session, transaction: Transaction) -> TicketTier:
    return db.scalar(select(Ticket.tier).where(Ticket.id == transaction.ticket_id))


def to_read(db: Session, transaction: Transaction) -> TransactionRead:
    tier = ticket_tier_of(db, transaction)
    return TransactionRead(
        reference=transaction.reference,
        ticket_tier=tier,
        status=transaction.status,
        amount_cents=transaction.amount_cents,
        quantity=transaction.quantity,
        phone=transaction.phone,
        expires_at=transaction.expires_at,
        confirmed_at=transaction.confirmed_at,
        created_at=transaction.created_at,
    )


def seed_ticket_tiers(db: Session) -> None:
    """Create any missing tier rows using the configured prices."""
    existing = set(db.scalars(select(Ticket.tier)).all())
    added = False
    for tier, spec in TIER_SPECS.items():
        if tier in existing:
            continue
        db.add(
            Ticket(
                tier=tier,
                name=spec.name,
                price_cents=int(getattr(settings, spec.price_setting)),
                is_student=spec.is_student,
                inventory_limit=None,
            )
        )
        added = True
    if added:
        db.commit()
