import logging

from sqlalchemy.orm import Session

from app.core.security import verify_password, create_password_reset_token
from app.domains.users.models import User
from app.domains.users.service import get_user_by_email

logger = logging.getLogger(__name__)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def process_forgot_password(db: Session, email: str) -> None:
    user = get_user_by_email(db, email)
    if user:
        token = create_password_reset_token(user.email)

        reset_link = f"http://localhost:3000/reset-password?token={token}"
        logger.info(f"Mock email sent to {user.email}: {reset_link}")
