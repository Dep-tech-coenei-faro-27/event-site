from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.tickets.service import get_ticket_for_user
from app.domains.users.models import User
from app.domains.users.schemas import UserProfileRead, UserRead, UserUpdate
from app.domains.users.service import update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileRead, status_code=status.HTTP_200_OK)
def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> UserProfileRead:
    ticket = get_ticket_for_user(db, current_user.id)
    qr_code = ticket.qr_payload if ticket is not None else None
    return UserProfileRead(
        **UserRead.model_validate(current_user).model_dump(),
        qr_code=qr_code,
    )


@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_current_user(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> UserRead:
    updated_user = update_user_profile(db, current_user, payload)
    return UserRead.model_validate(updated_user)
