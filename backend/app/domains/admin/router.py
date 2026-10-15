from fastapi import APIRouter, Depends, status

from app.domains.auth.dependencies import get_current_admin
from app.domains.users.models import User
from app.domains.users.schemas import UserRead

# Every route registered on this router needs a signed-in, verified administrator.
# The dependency lives on the router, not on each route, so a new admin endpoint
# cannot forget it.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_admin_profile(current_admin: User = Depends(get_current_admin)) -> UserRead:
    """Who the administrator is. The frontend uses it to decide whether to show the
    admin area: 200 for an admin, 403 for anyone else, 401 without a session."""
    return UserRead.model_validate(current_admin)
