import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.domains.auth.models import ResetPasswordToken, RevokedToken
from app.domains.users.models import User
from app.domains.users.service import get_user_by_email

logger = logging.getLogger(__name__)

DUMMY_PASSWORD_HASH = hash_password("dummy-password")


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user


def register_reset_token(
    db: Session, user_id: int, jti: str, expires_at: datetime
) -> ResetPasswordToken:
    reset_token = ResetPasswordToken(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def get_password_reset_token(db: Session, jti: str) -> ResetPasswordToken | None:
    return db.scalar(select(ResetPasswordToken).where(ResetPasswordToken.jti == jti))


def revoke_token(db: Session, jti: str, expires_at: datetime) -> None:
    db.add(RevokedToken(jti=jti, expires_at=expires_at))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def is_token_revoked(db: Session, jti: str) -> bool:
    return (
        db.scalar(select(RevokedToken.jti).where(RevokedToken.jti == jti)) is not None
    )
