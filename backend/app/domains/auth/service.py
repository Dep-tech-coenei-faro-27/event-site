from datetime import UTC, datetime
import logging

from app.domains.auth.models import ResetPasswordToken
from sqlalchemy.orm import Session

from app.core.security import verify_password
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

def register_reset_token(db: Session, jti: str, expires_at: datetime) -> ResetPasswordToken:
    reset_token = ResetPasswordToken(
        jti=jti,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def get_password_reset_token(db: Session, jti: str) -> ResetPasswordToken | None:
    return db.scalar(
        db.select(ResetPasswordToken).where(ResetPasswordToken.jti == jti)
    )
