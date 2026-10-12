from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.tickets.service import get_ticket_for_user
from app.domains.users.models import User
from app.domains.users.schemas import UserProfileRead, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserProfileRead,
    status_code=status.HTTP_200_OK,
)
def get_user_profile(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    ticket = get_ticket_for_user(db, current_user.id)

    profile_data = UserRead.model_validate(current_user).model_dump()
    profile_data["qr_code"] = (
        ticket.qr_string if ticket is not None else None
    )

    return UserProfileRead(**profile_data)
