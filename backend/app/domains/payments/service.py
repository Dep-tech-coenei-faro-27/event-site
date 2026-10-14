import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.payments.gateway import MBWayGateway, PaymentGatewayError
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import PaymentInitiateRequest, TransactionRead
from app.domains.tickets.service import issue_ticket_for_paid_transaction
from app.domains.users.models import StudentVerificationStatus, User

logger = logging.getLogger(__name__)

REFERENCE_PREFIX = "ENEI-"
REFERENCE_LENGTH = 15


class PaymentError(RuntimeError):
    status_code = 400


class TicketOfficeClosedError(PaymentError):
    status_code = 503


class TicketUnavailableError(PaymentError):
    status_code = 409


class TicketSoldOutError(PaymentError):
    status_code = 409


class StudentVerificationRequiredError(PaymentError):
    status_code = 403


class InvalidCallbackKeyError(PaymentError):
    status_code = 403


class CallbackTransactionNotFoundError(PaymentError):
    status_code = 404


class CallbackAmountMismatchError(PaymentError):
    status_code = 400


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _callback_key_matches(provided: str | None) -> bool:
    """Constant-time check of the ifthenpay anti-phishing key."""
    expected = settings.MBWAY_CALLBACK_KEY
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)


def _callback_amount_matches(raw_amount: str | None, amount_cents: int) -> bool:
    if raw_amount is None:
        return False
    try:
        return Decimal(raw_amount) * 100 == amount_cents
    except (InvalidOperation, ValueError):
        return False


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


def _reserved_quantity(db: Session, tier: TicketTierPrice, now: datetime) -> int:
    holds = db.scalar(
        select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
            Transaction.ticket_tier_id == tier.id,
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
) -> tuple[Transaction, TicketTierPrice]:
    # Lock the tier row so that the stock check and the reservation are a single
    # atomic step. Without it, two concurrent buyers of a limited tier can both read
    # the same remaining quantity and oversell the tier.
    tier = db.scalar(
        select(TicketTierPrice)
        .where(TicketTierPrice.tier == payload.ticket_tier)
        .with_for_update()
    )
    if tier is None:
        db.rollback()
        raise TicketUnavailableError("Ticket tier is not available")

    if tier.price_cents is None:
        db.rollback()
        raise TicketOfficeClosedError("Ticket sales are not open yet")

    if tier.is_student and (
        user.student_verification_status is not StudentVerificationStatus.VERIFIED
    ):
        db.rollback()
        raise StudentVerificationRequiredError(
            "Student verification is required to buy this ticket"
        )

    now = datetime.now(UTC)
    if tier.inventory_limit is not None:
        remaining = tier.inventory_limit - _reserved_quantity(db, tier, now)
        if remaining < payload.quantity:
            db.rollback()
            raise TicketSoldOutError("This ticket tier is sold out")

    amount_cents = tier.price_cents * payload.quantity
    transaction = Transaction(
        reference=generate_reference(db),
        user_id=user.id,
        ticket_tier_id=tier.id,
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
    return transaction, tier


def confirm_transaction(db: Session, transaction: Transaction) -> Transaction:
    """Record a successful payment and issue its ticket.

    Single source of truth for "the payment went through": both the provider
    callback and the status poll go through here, so the ticket is issued no
    matter how the confirmation arrives. Idempotent: a repeated call returns the
    same transaction and never duplicates the ticket.
    """
    if transaction.status is not TransactionStatus.CONFIRMED:
        transaction.status = TransactionStatus.CONFIRMED
        transaction.confirmed_at = datetime.now(UTC)
        db.commit()
        db.refresh(transaction)

    issue_ticket_for_paid_transaction(
        db, user_id=transaction.user_id, transaction_reference=transaction.reference
    )
    return transaction


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
        confirm_transaction(db, transaction)
        return

    transaction.status = provider_status
    db.commit()
    db.refresh(transaction)


def handle_payment_callback(
    db: Session,
    *,
    key: str | None,
    reference: str | None,
    amount: str | None,
) -> Transaction:
    """Apply an ifthenpay payment callback to a transaction.

    Trust only callbacks that carry our anti-phishing key, and only confirm a
    payment whose value matches what was charged. A callback only confirms a
    transaction that is still ``pending``: one that already ``failed`` or
    ``expired`` is answered 200 (so ifthenpay stops retrying) but left untouched
    and logged, because an unexpected late payment needs a manual look. Idempotent:
    a repeated callback returns the same transaction and never duplicates the
    ticket.
    """
    if not _callback_key_matches(key):
        raise InvalidCallbackKeyError("Invalid callback key")

    if not reference:
        raise CallbackTransactionNotFoundError("Missing transaction reference")

    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference).with_for_update()
    )
    if transaction is None:
        raise CallbackTransactionNotFoundError("Unknown transaction reference")

    if not _callback_amount_matches(amount, transaction.amount_cents):
        raise CallbackAmountMismatchError(
            "Callback amount does not match the transaction"
        )

    if transaction.status in (TransactionStatus.FAILED, TransactionStatus.EXPIRED):
        logger.warning(
            "MB WAY callback for %s ignored: transaction is %s",
            transaction.reference,
            transaction.status.value,
        )
        return transaction

    return confirm_transaction(db, transaction)


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
    return db.scalar(
        select(TicketTierPrice.tier).where(
            TicketTierPrice.id == transaction.ticket_tier_id
        )
    )


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
