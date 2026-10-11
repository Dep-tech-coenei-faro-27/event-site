from app.domains.auth.dependencies import get_current_session
from app.domains.users.models import User
from app.domains.users.schemas import UserProfileRead, UserRead
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserProfileRead,
    status_code=status.HTTP_200_OK,
)
def get_user_profile(
    current_user: User = Depends(get_current_session),
) -> UserProfileRead:

    return UserProfileRead.model_validate(current_user)