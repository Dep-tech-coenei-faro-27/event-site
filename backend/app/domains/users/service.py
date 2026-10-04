from datetime import UTC, datetime

from app.domains.auth.models import ResetPasswordToken
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domains.users.models import User
from app.domains.users.schemas import UserRegister


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    return db.scalar(select(User).where(User.email == normalized_email))


def create_user(db: Session, payload: UserRegister) -> User:
    user = User(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(user)
    return user


def mark_user_verified(db: Session, user: User) -> User:
    user.is_verified = True
    user.email_verified_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user

def reset_user_password(db: Session, user: User, new_password: str, token: ResetPasswordToken) -> User:
    user.password_hash = hash_password(new_password)
    token.used_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user