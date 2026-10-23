import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from app.core.config import settings
from app.core.rate_limit import RateLimit, client_ip, enforce_rate_limit
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.payments.events import events
from app.domains.payments.gateway import (
    MBWayGateway,
    PaymentGatewayError,
    get_mbway_gateway,
)
from app.domains.payments.schemas import (
    PaymentInitiateRequest,
    TicketTierRead,
    TransactionRead,
)
from app.domains.payments.service import (
    PaymentError,
    get_transaction,
    handle_payment_callback,
    handle_stripe_event,
    initiate_payment,
    list_ticket_tiers,
    to_read,
)
from app.domains.payments.stream import authorize, event_stream
from app.domains.payments.stripe_webhook import (
    InvalidStripeSignatureError,
    verify_signature,
)
from app.domains.users.models import User

router = APIRouter(prefix="/payment", tags=["payment"])

logger = logging.getLogger(__name__)

PAYMENT_INITIATE_FAILED_MESSAGE = "Payment could not be initiated. Please try again."


@router.get(
    "/tiers", response_model=list[TicketTierRead], status_code=status.HTTP_200_OK
)
def read_tiers(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> list[TicketTierRead]:
    """Public: the modalities, their price and whether each can be bought now."""
    rule = RateLimit(
        "payment_tiers", settings.RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE, 60
    )
    enforce_rate_limit(db, (rule,), client_ip(request))
    response.headers["Cache-Control"] = "no-store"
    return list_ticket_tiers(db)


@router.post(
    "/initiate",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def initiate(
    payload: PaymentInitiateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    gateway: MBWayGateway = Depends(get_mbway_gateway),
) -> TransactionRead:
    rule = RateLimit("payment", settings.RATE_LIMIT_PAYMENT_PER_MINUTE, 60)
    enforce_rate_limit(db, (rule,), str(current_user.id))

    try:
        transaction, _ = initiate_payment(db, current_user, payload, gateway)
    except PaymentGatewayError as exc:
        logger.warning("MB WAY gateway error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=PAYMENT_INITIATE_FAILED_MESSAGE,
        ) from exc
    except PaymentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return to_read(db, transaction)


@router.get(
    "/transactions/{reference}",
    response_model=TransactionRead,
    status_code=status.HTTP_200_OK,
)
def read_transaction(
    reference: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    gateway: MBWayGateway = Depends(get_mbway_gateway),
) -> TransactionRead:
    rule = RateLimit(
        "payment_status",
        settings.RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE,
        60,
    )
    enforce_rate_limit(db, (rule,), str(current_user.id))

    transaction = get_transaction(db, current_user, reference, gateway)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return to_read(db, transaction)


@router.get("/transactions/{reference}/events")
async def stream_transaction_events(
    reference: str, request: Request
) -> StreamingResponse:
    """Live status of a payment (Server-Sent Events): the current status first, then
    every change, until the payment is decided. Replaces asking again every 2 s."""
    user_id = await run_in_threadpool(authorize, request, reference)
    events.bind_loop(asyncio.get_running_loop())
    queue = events.subscribe(reference, user_id, settings.PAYMENT_EVENTS_MAX_PER_USER)
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many open streams",
        )
    return StreamingResponse(
        event_stream(reference, user_id, queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        # Also frees the stream if the response never starts (idempotent).
        background=BackgroundTask(events.unsubscribe, reference, user_id, queue),
    )


@router.get(
    "/callback",
    status_code=status.HTTP_200_OK,
)
def payment_callback(
    request: Request,
    db: Session = Depends(get_db),
    key: str | None = Query(default=None),
    apk: str | None = Query(default=None),
    order_id: str | None = Query(default=None, alias="orderId"),
    oid: str | None = Query(default=None),
    amount: str | None = Query(default=None),
    val: str | None = Query(default=None),
) -> dict[str, str]:
    """Public ifthenpay callback: confirms a paid transaction and issues its ticket.

    ifthenpay calls this by GET and repeats until it gets a 200, so a validation
    error (wrong anti-phishing key, unknown reference or mismatched amount) must
    not be swallowed. Accepts the legacy ``key/orderId/amount`` names and the
    current ``apk/oid/val`` ones.
    """
    rule = RateLimit(
        "payment_callback",
        settings.RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE,
        60,
    )
    enforce_rate_limit(db, (rule,), client_ip(request))

    try:
        handle_payment_callback(
            db,
            key=key or apk,
            reference=order_id or oid,
            amount=amount or val,
        )
    except PaymentError as exc:
        logger.warning("MB WAY callback rejected: %s", exc)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return {"status": "ok"}


def _process_stripe_webhook(
    db: Session, request: Request, payload: bytes, signature: str | None
) -> None:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook is not configured.",
        )
    try:
        verify_signature(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
            tolerance_seconds=settings.STRIPE_WEBHOOK_TOLERANCE_SECONDS,
        )
    except InvalidStripeSignatureError as exc:
        # Only the bad ones are counted: Stripe sends a burst from a few addresses
        # when the sales open, and a valid event must never be turned away.
        rule = RateLimit(
            "stripe_webhook_invalid",
            settings.RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE,
            60,
        )
        enforce_rate_limit(db, (rule,), client_ip(request))
        logger.warning("Stripe webhook rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature."
        ) from exc

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload."
        ) from exc
    if not isinstance(event, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload."
        )
    handle_stripe_event(db, event)


@router.post("/stripe/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, str]:
    """Public: Stripe tells us a payment ended.

    Authenticated by the signature of the raw body (``STRIPE_WEBHOOK_SECRET``), not
    by a session. A signature or payload error answers 400 and a configuration gap
    503; everything else, even an event about a payment we do not know, answers 200
    so Stripe stops repeating it. An unexpected failure answers 500 and Stripe tries
    again.
    """
    payload = await request.body()
    await run_in_threadpool(
        _process_stripe_webhook,
        db,
        request,
        payload,
        request.headers.get("Stripe-Signature"),
    )
    return {"status": "ok"}
