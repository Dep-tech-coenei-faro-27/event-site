from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.domains.auth.models import ResetPasswordToken
from app.domains.users.models import User


def delete_unverified_users(db: Session, older_than_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    result = db.execute(
        delete(User).where(User.is_verified.is_(False), User.created_at < cutoff)
    )
    db.commit()
    return result.rowcount


def delete_expired_reset_tokens(db: Session, older_than_days: int = 1) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    result = db.execute(
        delete(ResetPasswordToken).where(ResetPasswordToken.expires_at < cutoff)
    )
    db.commit()
    return result.rowcount


def main() -> None:
    with SessionLocal() as db:
        deleted = delete_unverified_users(db, settings.UNVERIFIED_ACCOUNT_TTL_DAYS)
        tokens = delete_expired_reset_tokens(db)
    print(
        f"Deleted {deleted} unverified accounts "
        f"older than {settings.UNVERIFIED_ACCOUNT_TTL_DAYS} days "
        f"and {tokens} expired password reset tokens"
    )


if __name__ == "__main__":
    main()
