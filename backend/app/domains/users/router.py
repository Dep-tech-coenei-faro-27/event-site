from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.users.models import User
from app.domains.users.schemas import UserRead, UserUpdate
from app.domains.users.service import update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_current_user(user: User = Depends(get_current_verified_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_current_user_profile(
        user: User = Depends(get_current_verified_user),
        payload: UserUpdate = Depends(),
        db: Session = Depends(get_db),
) -> UserRead:
    updated_user = update_user_profile(db, user, payload)
    return UserRead.model_validate(updated_user)
