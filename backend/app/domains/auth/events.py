import hashlib
import hmac
import logging

from app.core.config import settings

logger = logging.getLogger("app.auth.events")

LOGIN_SUCCEEDED = "login_succeeded"
LOGIN_FAILED = "login_failed"
PASSWORD_CHANGED = "password_changed"


def hash_ip(ip: str) -> str:
    """A keyed hash of the IP, so the same address can be followed in the logs.

    A plain hash of an IPv4 address is reversed by trying all of them, so the
    hash is keyed with a value derived from the JWT secret.
    """
    key = hashlib.sha256(
        b"auth-event-ip:" + settings.JWT_SECRET_KEY.encode("utf-8")
    ).digest()
    return hmac.new(key, ip.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def log_auth_event(
    event: str, ip: str, user_id: int | None = None, detail: str | None = None
) -> None:
    """Log an authentication event with the user id and the hashed IP only.

    Never pass the email, the password or anything typed by the visitor.
    """
    logger.info(
        "auth_event=%s user_id=%s ip_hash=%s detail=%s",
        event,
        user_id if user_id is not None else "-",
        hash_ip(ip),
        detail or "-",
    )
