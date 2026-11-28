from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.payments.gateway import MBWayGateway, get_mbway_gateway_or_none
from app.domains.payments.schemas import ShirtSizeUpdate
from app.domains.payments.service import (
    PaymentError,
    account_payment_overview,
    refresh_users_pending_payment,
    set_shirt_size,
)
from app.domains.tickets.models import PaymentStatus
from app.domains.tickets.service import get_ticket_for_user
from app.domains.users.models import User
from app.domains.users.schemas import (
    TicketSummaryRead,
    UserProfileRead,
    UserRead,
    UserUpdate,
)
from app.domains.users.service import update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileRead, status_code=status.HTTP_200_OK)
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    gateway: MBWayGateway | None = Depends(get_mbway_gateway_or_none),
) -> UserProfileRead:
    # If they left the waiting page, settle their payment now rather than wait for the
    # webhook: the ticket shows as soon as the provider says it is paid.
    refresh_users_pending_payment(db, current_user, gateway)
    ticket = get_ticket_for_user(db, current_user.id)
    paid = ticket is not None and ticket.payment_status == PaymentStatus.PAID
    qr_code = ticket.qr_payload if paid else None
    return UserProfileRead(
        **UserRead.model_validate(current_user).model_dump(),
        qr_code=qr_code,
        **account_payment_overview(db, current_user),
    )


@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_current_user(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> UserRead:
    updated_user = update_user_profile(db, current_user, payload)
    return UserRead.model_validate(updated_user)


@router.put(
    "/me/shirt-size",
    response_model=TicketSummaryRead,
    status_code=status.HTTP_200_OK,
)
def update_shirt_size(
    payload: ShirtSizeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> TicketSummaryRead:
    """Set the shirt size of the person's ticket (student modalities only).

    404 without a ticket that has a shirt; 409 after ``SHIRT_SIZE_CHANGE_UNTIL``.
    """
    try:
        set_shirt_size(db, current_user, payload.shirt_size)
    except PaymentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return TicketSummaryRead(**account_payment_overview(db, current_user)["ticket"])
