import hmac
import logging
import secrets
import threading
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.payments.gateway import (
    MBWayGateway,
    PaymentGatewayError,
    UnrecognisedStatusError,
)
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import (
    PaymentInitiateRequest,
    TicketTierRead,
    TransactionRead,
)
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.tickets.service import (
    PaymentNotConfirmedError,
    TicketNotFoundError,
    issue_ticket_for_paid_transaction,
)
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


class AlreadyHasTicketError(PaymentError):
    status_code = 409


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


def _reserved_quantity(db: Session, tier: TicketTierPrice) -> int:
    """Seats taken: paid ones, and the ones reserved for a payment that is waiting.

    A waiting payment keeps its seat for as long as it is ``pending``, however long
    that takes: the seat is released only when the provider says the payment is over
    (paid payments stay counted, failed and expired ones are not). That is what
    makes it impossible to sell a seat that someone is about to pay for.
    """
    holds = db.scalar(
        select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
            Transaction.ticket_tier_id == tier.id,
            Transaction.status.in_(
                (TransactionStatus.CONFIRMED, TransactionStatus.PENDING)
            ),
        )
    )
    return int(holds or 0)


def _refuse_if_user_already_buying(db: Session, user: User) -> None:
    """Refuse a second purchase: a ticket already exists, or a payment is in flight.

    Without this, a person who starts two payments and pays both is charged twice
    but can only hold one ticket (the unique index on ``tickets``), and the second
    confirmation fails after the money has moved.
    """
    has_ticket = db.scalar(
        select(Ticket.id)
        .where(
            Ticket.user_id == user.id, Ticket.payment_status != PaymentStatus.CANCELLED
        )
        .limit(1)
    )
    has_open_payment = db.scalar(
        select(Transaction.id)
        .where(
            Transaction.user_id == user.id,
            Transaction.status == TransactionStatus.PENDING,
        )
        .limit(1)
    )
    if has_ticket is not None or has_open_payment is not None:
        db.rollback()
        raise AlreadyHasTicketError(
            "You already have a ticket or a payment in progress"
        )


def _settle_pending(
    db: Session, transaction: Transaction, status: TransactionStatus
) -> None:
    """Move a pending transaction to ``failed`` or ``expired``.

    The row is locked and read again first: a callback may have confirmed the
    payment while we were talking to the provider, and a confirmed payment must
    never be overwritten by a stale ``expired`` or ``failed``.
    """
    db.refresh(transaction, with_for_update=True)
    if transaction.status is TransactionStatus.PENDING:
        transaction.status = status
    db.commit()
    db.refresh(transaction)


ABANDONED_CHECKS_PER_REQUEST = 10


def _free_abandoned_seats(
    db: Session, tier_name: TicketTier, gateway: MBWayGateway
) -> None:
    """Before refusing a sale for lack of stock, settle the payments nobody follows.

    A waiting payment holds its seat until the provider ends it. One that was
    abandoned (the person closed the page) is only settled when someone asks the
    provider, so when the modality looks full we ask about the oldest overdue ones
    first. Done outside any lock, a few at a time.
    """
    tier = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == tier_name))
    if tier is None or tier.inventory_limit is None:
        return
    if tier.inventory_limit - _reserved_quantity(db, tier) >= 1:
        return
    overdue = db.scalars(
        select(Transaction)
        .where(
            Transaction.ticket_tier_id == tier.id,
            Transaction.status == TransactionStatus.PENDING,
            Transaction.expires_at <= datetime.now(UTC),
        )
        .order_by(Transaction.expires_at)
        .limit(ABANDONED_CHECKS_PER_REQUEST)
    ).all()
    for old in overdue:
        _sync_provider_status(db, old, gateway)


def initiate_payment(
    db: Session,
    user: User,
    payload: PaymentInitiateRequest,
    gateway: MBWayGateway,
) -> tuple[Transaction, TicketTierPrice]:
    # A payment of this person that is past its deadline may already be over (or
    # paid) at the provider. Ask before deciding anything, outside any lock.
    user_id = user.id
    stale = db.scalars(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.PENDING,
            Transaction.expires_at <= datetime.now(UTC),
        )
    ).all()
    for old in stale:
        _sync_provider_status(db, old, gateway)
    _free_abandoned_seats(db, payload.ticket_tier, gateway)

    # One ticket per person. The user row is locked first so two simultaneous requests
    # from the same person cannot both pass the check below; the order (user, then
    # tier) is the same everywhere, so it cannot deadlock.
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    _refuse_if_user_already_buying(db, user)

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
        remaining = tier.inventory_limit - _reserved_quantity(db, tier)
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
        _settle_pending(db, transaction, TransactionStatus.FAILED)
        raise

    transaction.provider_reference = payment.provider_reference
    db.commit()
    db.refresh(transaction)
    return transaction, tier


def _holds_another_active_ticket(db: Session, transaction: Transaction) -> bool:
    return (
        db.scalar(
            select(Ticket.id)
            .where(
                Ticket.user_id == transaction.user_id,
                Ticket.payment_status != PaymentStatus.CANCELLED,
                Ticket.transaction_reference != transaction.reference,
            )
            .limit(1)
        )
        is not None
    )


def _has_room(db: Session, transaction: Transaction) -> bool:
    """Whether a payment that is not ``pending`` any more can still get its seat.

    A waiting payment always has its seat, so this is only asked for one that was
    marked ``failed`` or ``expired`` and is then paid after all (the provider
    answered in the meantime, or its creation reported an error that was not one).
    The seat was released, so the stock is checked again with the modality row
    locked, like ``initiate_payment`` does: we never sell what we do not have.
    """
    if transaction.status is TransactionStatus.PENDING:
        return True
    tier = db.scalar(
        select(TicketTierPrice)
        .where(TicketTierPrice.id == transaction.ticket_tier_id)
        .with_for_update()
    )
    if tier is None or tier.inventory_limit is None:
        return True
    return tier.inventory_limit - _reserved_quantity(db, tier) >= transaction.quantity


def _record_refund_due(
    db: Session, transaction: Transaction, reason: str
) -> Transaction:
    """The money arrived but there is no ticket to give: the payment is refunded.

    A last resort that should not happen: a waiting payment holds its seat and
    blocks a second payment of the same person. It can still follow an unexpected
    sequence (a payment marked ``failed`` that is paid after all, with the modality
    sold out meanwhile, or the person already holding a ticket). The payment is kept
    as ``refund_due``, which holds no stock, and logged loudly. List them with the
    query in ``docs/deploy.md``.
    """
    transaction.status = TransactionStatus.REFUND_DUE
    transaction.confirmed_at = transaction.confirmed_at or datetime.now(UTC)
    db.commit()
    db.refresh(transaction)
    logger.error(
        "Payment %s needs a refund: %s. Refund it by hand.",
        transaction.reference,
        reason,
    )
    return transaction


def confirm_transaction(db: Session, transaction: Transaction) -> Transaction:
    """Record a successful payment and issue its ticket.

    Single source of truth for "the payment went through": both the provider
    callback and the status poll go through here, so the ticket is issued no
    matter how the confirmation arrives. Idempotent: a repeated call returns the
    same transaction and never duplicates the ticket.

    The transaction row stays locked until the ticket is committed, so two
    confirmations of the same payment (poll and poll, or poll and callback) run one
    after the other. The status and the ticket are saved together. No ticket is
    issued, and the payment is kept for a refund, when the person already holds a
    ticket from another payment or when a late payment finds the modality sold out.
    """
    db.refresh(transaction, with_for_update=True)
    if transaction.status in (TransactionStatus.REFUND_DUE, TransactionStatus.REFUNDED):
        return transaction  # already decided: a repeated callback changes nothing

    if _holds_another_active_ticket(db, transaction):
        return _record_refund_due(db, transaction, "the person already has a ticket")

    if transaction.status is not TransactionStatus.CONFIRMED:
        if not _has_room(db, transaction):
            return _record_refund_due(db, transaction, "the modality sold out")
        transaction.status = TransactionStatus.CONFIRMED
        transaction.confirmed_at = datetime.now(UTC)

    try:
        issue_ticket_for_paid_transaction(
            db,
            user_id=transaction.user_id,
            transaction_reference=transaction.reference,
        )
    except IntegrityError:
        # Lost a race: either the same payment was confirmed by someone else in
        # the meantime, or the person's other payment got its ticket first.
        db.rollback()
        db.refresh(transaction)
        issued = db.scalar(
            select(Ticket.id).where(
                Ticket.transaction_reference == transaction.reference
            )
        )
        if issued is not None:
            return transaction
        if _holds_another_active_ticket(db, transaction):
            return _record_refund_due(
                db, transaction, "the person already has a ticket"
            )
        raise
    except PaymentNotConfirmedError:
        # The ticket of this payment was cancelled (a refund). A repeated callback
        # must not bring it back, and ifthenpay must stop retrying.
        db.commit()
        logger.warning(
            "Payment %s confirmed again but its ticket is cancelled; left as is",
            transaction.reference,
        )
        db.refresh(transaction)
        return transaction
    # Saves the status when the ticket already existed and nothing else committed.
    db.commit()
    db.refresh(transaction)
    return transaction


_asked_at: dict[str, float] = {}
_asked_lock = threading.Lock()
_clock = time.monotonic  # replaced in tests


def _should_ask_provider(key: str) -> bool:
    """Whether the provider may be asked about ``key`` now.

    At most one question per payment every ``PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS``.
    The memory is per process (the backend runs one), so with more processes each
    would ask on its own. Skipping a question never changes a payment: it stays as it
    is until the next one, or until the callback arrives.
    """
    interval = settings.PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS
    if interval <= 0:
        return True
    now = _clock()
    with _asked_lock:
        last = _asked_at.get(key)
        if last is not None and now - last < interval:
            return False
        _asked_at[key] = now
        if len(_asked_at) > 4096:  # forget what is long past
            for old_key, asked in list(_asked_at.items()):
                if now - asked > 10 * interval:
                    del _asked_at[old_key]
    return True


def _sync_provider_status(
    db: Session, transaction: Transaction, gateway: MBWayGateway
) -> None:
    """Ask the provider for the real state of a pending payment and persist it.

    The provider is the source of truth: a confirmed payment must reach the
    frontend even if the local ``expires_at`` window already passed, and a
    failed/expired one must not stay ``pending``. A payment the provider still
    reports as waiting stays ``pending`` and keeps its seat, even past its local
    deadline (``expires_at`` is the time the person has to approve, not the moment
    the seat is released). When the gateway is unreachable the answer is unknown, so
    the payment also stays ``pending`` and the poll keeps working. A payment the
    provider cannot resolve (no reference, or an unreadable answer) is expired a long
    time after its deadline so that it does not hold its seat for ever.
    """
    reference = transaction.reference
    provider_reference = transaction.provider_reference
    expires_at = _as_utc(transaction.expires_at)
    # Release the pooled database connection before the network call: a slow
    # provider must not keep a connection busy while we wait for its answer.
    db.commit()

    if provider_reference and not _should_ask_provider(reference):
        return  # asked a moment ago: nothing can have changed that the callback misses

    # "Unresolved" means the provider could not tell us: we never saved its reference,
    # or it answered something we cannot read. (An unreachable provider is not
    # unresolved: it is an outage, and the payments stay as they are.)
    unresolved = False
    provider_status = TransactionStatus.PENDING
    if not provider_reference:
        unresolved = True
        logger.warning("Payment %s has no provider reference to ask about", reference)
    else:
        try:
            provider_status = gateway.get_status(
                reference=reference,
                provider_reference=provider_reference,
            )
        except UnrecognisedStatusError:
            unresolved = True
        except PaymentGatewayError:
            logger.warning(
                "MB WAY status poll failed for %s; keeping stored status",
                reference,
            )

    if provider_status is TransactionStatus.PENDING:
        # Still waiting, whatever the local deadline says: only the provider can end
        # a payment, and until then it keeps its seat. The one exception is a payment
        # the provider cannot resolve for a long time: it would hold its seat for ever.
        limit = timedelta(seconds=settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS)
        if unresolved and expires_at + limit < datetime.now(UTC):
            logger.error(
                "Payment %s could not be resolved with the provider for over %s s "
                "after its deadline: expired. If it was paid, it needs a look.",
                reference,
                settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS,
            )
            _settle_pending(db, transaction, TransactionStatus.EXPIRED)
        return
    if provider_status is TransactionStatus.CONFIRMED:
        confirm_transaction(db, transaction)
        return

    _settle_pending(db, transaction, provider_status)


def cancel_ticket(db: Session, ticket_id: int) -> Ticket:
    """Cancel a ticket and free its seat: the payment becomes ``refunded``.

    The caller refunds the money (the gateway, or by hand). The person can buy again,
    and the seat counts as free for the next buyer. Idempotent. The transaction is
    locked before the ticket, the same order as ``confirm_transaction``, so a
    repeated callback arriving at the same time cannot deadlock with it.
    """
    reference = db.scalar(
        select(Ticket.transaction_reference).where(Ticket.id == ticket_id)
    )
    if reference is None:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found")
    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference).with_for_update()
    )
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket.payment_status is not PaymentStatus.CANCELLED:
        ticket.payment_status = PaymentStatus.CANCELLED
        if (
            transaction is not None
            and transaction.status is TransactionStatus.CONFIRMED
        ):
            transaction.status = TransactionStatus.REFUNDED
        db.commit()
        db.refresh(ticket)
    return ticket


def handle_payment_callback(
    db: Session,
    *,
    key: str | None,
    reference: str | None,
    amount: str | None,
) -> Transaction:
    """Apply an ifthenpay payment callback to a transaction.

    Trust only callbacks that carry our anti-phishing key, and only confirm a
    payment whose value matches what was charged. ifthenpay only calls this when
    the money has been paid, so a callback for a transaction that already
    ``failed`` or ``expired`` locally is a late payment: it is confirmed like any
    other (the person paid and gets the ticket) and logged, unless the modality sold
    out meanwhile or the person already has a ticket: ``confirm_transaction`` then
    keeps the payment as ``refund_due`` for a manual refund. Idempotent: a repeated
    callback returns the same transaction and never duplicates the ticket.
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
            "Late MB WAY payment for %s: the transaction was %s locally",
            transaction.reference,
            transaction.status.value,
        )

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


def account_payment_overview(db: Session, user: User) -> dict:
    """What the account page needs to know about the person's purchase.

    The active ticket (with its modality), the payment that is waiting, and a payment
    that arrived without a ticket and will be refunded. Each is ``None`` if absent.
    """
    ticket = db.execute(
        select(Ticket, TicketTierPrice)
        .join(Transaction, Transaction.reference == Ticket.transaction_reference)
        .join(TicketTierPrice, TicketTierPrice.id == Transaction.ticket_tier_id)
        .where(
            Ticket.user_id == user.id,
            Ticket.payment_status == PaymentStatus.PAID,
        )
        .order_by(Ticket.id.desc())
        .limit(1)
    ).first()
    waiting = db.execute(
        select(Transaction, TicketTierPrice)
        .join(TicketTierPrice, TicketTierPrice.id == Transaction.ticket_tier_id)
        .where(
            Transaction.user_id == user.id,
            Transaction.status == TransactionStatus.PENDING,
        )
        .order_by(Transaction.id.desc())
        .limit(1)
    ).first()
    refund = db.scalar(
        select(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.status == TransactionStatus.REFUND_DUE,
        )
        .order_by(Transaction.id.desc())
        .limit(1)
    )
    return {
        "ticket": None
        if ticket is None
        else {
            "reference": ticket[0].transaction_reference,
            "tier": ticket[1].tier.value,
            "tier_name": ticket[1].name,
            "holder_name": user.name,
            "paid_at": ticket[0].paid_at,
        },
        "pending_payment": None
        if waiting is None
        else {
            "reference": waiting[0].reference,
            "tier": waiting[1].tier.value,
            "tier_name": waiting[1].name,
            "amount_cents": waiting[0].amount_cents,
            "expires_at": waiting[0].expires_at,
        },
        "refund_due": None
        if refund is None
        else {"reference": refund.reference, "amount_cents": refund.amount_cents},
    }


def list_ticket_tiers(db: Session) -> list[TicketTierRead]:
    """The modalities with their price and whether each can be bought right now.

    ``sale_open`` is false while payments are off or the modality has no price.
    ``available`` is also false when every seat is taken or reserved for a payment
    that is waiting. Read-only: it does not ask the provider about anything.
    """
    order = {tier: index for index, tier in enumerate(TicketTier)}
    rows = sorted(db.scalars(select(TicketTierPrice)), key=lambda r: order[r.tier])
    payments_on = settings.PAYMENTS_MODE != "off"
    result = []
    for row in rows:
        sale_open = payments_on and row.price_cents is not None
        has_room = row.inventory_limit is None or (
            row.inventory_limit - _reserved_quantity(db, row) >= 1
        )
        result.append(
            TicketTierRead(
                tier=row.tier,
                name=row.name,
                price_cents=row.price_cents,
                is_student=row.is_student,
                sale_open=sale_open,
                available=sale_open and has_room,
            )
        )
    return result


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
