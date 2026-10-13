from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.users.models import User
from app.domains.users.schemas import UserRead, UserUpdate
from app.domains.users.service import update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: User = Depends(get_current_verified_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_current_user(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> UserRead:
    updated_user = update_user_profile(db, current_user, payload)
    return UserRead.model_validate(updated_user)
