import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import RateLimit, enforce_rate_limit
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.payments.gateway import (
    MBWayGateway,
    PaymentGatewayError,
    get_mbway_gateway,
)
from app.domains.payments.schemas import PaymentInitiateRequest, TransactionRead
from app.domains.payments.service import (
    PaymentError,
    get_transaction,
    initiate_payment,
    to_read,
)
from app.domains.users.models import User

router = APIRouter(prefix="/payment", tags=["payment"])

logger = logging.getLogger(__name__)

PAYMENT_INITIATE_FAILED_MESSAGE = "Payment could not be initiated. Please try again."


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
) -> TransactionRead:
    transaction = get_transaction(db, current_user, reference)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return to_read(db, transaction)
