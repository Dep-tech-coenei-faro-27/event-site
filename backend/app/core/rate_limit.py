import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from sqlalchemy import BigInteger, Integer, String, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.config import settings
from app.db.base import Base

PURGE_PROBABILITY = 0.01
PURGE_AFTER_SECONDS = 86400

UPSERT_ATTEMPT = text(
    """
    INSERT INTO rate_limits (key, window_start, attempts)
    VALUES (:key, :now, 1)
    ON CONFLICT (key) DO UPDATE SET
        attempts = CASE
            WHEN rate_limits.window_start <= :expired THEN 1
            ELSE rate_limits.attempts + 1
        END,
        window_start = CASE
            WHEN rate_limits.window_start <= :expired THEN :now
            ELSE rate_limits.window_start
        END
    RETURNING attempts, window_start
    """
)


class RateLimitCounter(Base):
    __tablename__ = "rate_limits"

    key: Mapped[str] = mapped_column(String(400), primary_key=True)
    window_start: Mapped[int] = mapped_column(BigInteger, index=True)
    attempts: Mapped[int] = mapped_column(Integer)


@dataclass(frozen=True)
class RateLimit:
    name: str
    limit: int
    window_seconds: int


def current_time() -> int:
    return int(time.time())


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    db: Session, rules: Sequence[RateLimit], identifier: str
) -> None:
    """Apply every rule to the same identifier (see ``enforce_rate_limits``)."""
    enforce_rate_limits(db, [(rule, identifier) for rule in rules])


def enforce_rate_limits(db: Session, checks: Sequence[tuple[RateLimit, str]]) -> None:
    """Count one attempt per (rule, identifier) pair and raise 429 if any is over.

    Counters live in the database so every worker shares them. Each rule is a
    fixed window that starts at the first attempt; blocked attempts still count.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    now = current_time()
    retry_after = 0

    for rule, identifier in checks:
        key = f"{rule.name}:{rule.window_seconds}:{identifier.strip().lower()}"
        row = db.execute(
            UPSERT_ATTEMPT,
            {
                "key": key,
                "now": now,
                "expired": now - rule.window_seconds,
            },
        ).one()
        if row.attempts > rule.limit:
            retry_after = max(
                retry_after, row.window_start + rule.window_seconds - now, 1
            )

    if random.random() < PURGE_PROBABILITY:
        db.execute(
            text("DELETE FROM rate_limits WHERE window_start < :cutoff"),
            {"cutoff": now - PURGE_AFTER_SECONDS},
        )
    db.commit()

    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
