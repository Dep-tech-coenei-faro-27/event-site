import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import RateLimit, client_ip, enforce_rate_limit
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
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
    initiate_payment,
    list_ticket_tiers,
    to_read,
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
