from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domains.auth.models import ResetPasswordToken
from app.domains.users.models import User
from app.domains.users.schemas import UserRegister


class ResetTokenUsedError(Exception):
    """The password reset token was already used."""


class AccountAlreadyVerifiedError(Exception):
    """The account was verified, so it can no longer be replaced."""


class VerificationLinkOutdatedError(Exception):
    """The account changed after the verification link was checked."""


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


def replace_unverified_user(db: Session, user: User, payload: UserRegister) -> User:
    """Give an account that was never verified to whoever registers it now.

    This stops someone from keeping an email address blocked by registering it
    first. The old verification links stop working because they are tied to the
    previous password, and pending reset links and sessions are closed.
    """
    password_hash = hash_password(payload.password)
    now = datetime.now(UTC)

    replaced = db.execute(
        update(User)
        .where(User.id == user.id, User.is_verified.is_(False))
        .values(
            name=payload.name.strip(),
            password_hash=password_hash,
            created_at=now,
            token_version=User.token_version + 1,
        )
    ).rowcount
    if replaced != 1:
        db.rollback()
        raise AccountAlreadyVerifiedError
    db.execute(
        update(ResetPasswordToken)
        .where(
            ResetPasswordToken.user_id == user.id,
            ResetPasswordToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.commit()
    db.refresh(user)
    return user


def mark_user_verified(db: Session, user: User) -> User:
    """Verify the account, but only if its password is still the one the link was for.

    The link was checked against ``user.password_hash`` a moment ago. If someone
    registered the email again in between, the password changed and the account
    must not become verified with it.
    """
    verified = db.execute(
        update(User)
        .where(
            User.id == user.id,
            User.password_hash == user.password_hash,
            User.is_verified.is_(False),
        )
        .values(is_verified=True, email_verified_at=datetime.now(UTC))
    ).rowcount
    db.commit()
    db.refresh(user)
    if verified != 1 and not user.is_verified:
        raise VerificationLinkOutdatedError
    return user


def update_user_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    user.token_version = User.token_version + 1
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(
    db: Session, user: User, new_password: str, token: ResetPasswordToken
) -> User:
    password_hash = hash_password(new_password)
    now = datetime.now(UTC)

    claimed = db.execute(
        update(ResetPasswordToken)
        .where(ResetPasswordToken.id == token.id, ResetPasswordToken.used_at.is_(None))
        .values(used_at=now)
    ).rowcount
    if claimed != 1:
        db.rollback()
        raise ResetTokenUsedError

    db.execute(
        update(ResetPasswordToken)
        .where(
            ResetPasswordToken.user_id == user.id,
            ResetPasswordToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    user.password_hash = password_hash
    user.token_version = User.token_version + 1
    if not user.is_verified:
        user.is_verified = True
        user.email_verified_at = now
    db.commit()
    db.refresh(user)
    return user
