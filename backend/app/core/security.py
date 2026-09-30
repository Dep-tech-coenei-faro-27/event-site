from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

import app.core.config as config

BCRYPT_MAX_PASSWORD_BYTES = 72
BCRYPT_ROUNDS = 12

ACCESS_TOKEN_TYPE = "access"
EMAIL_VERIFICATION_TOKEN_TYPE = "email_verification"


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password exceeds the maximum length supported by bcrypt")
    hashed = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    )
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str, role: str, expires_delta: timedelta | None = None
) -> str:
    issued_at = datetime.now(UTC)

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=config.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": subject,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        config.settings.JWT_SECRET_KEY,
        algorithm=config.settings.JWT_ALGORITHM,
    )


def create_email_verification_token(email: str) -> str:
    issued_at = datetime.now(UTC)

    expire = datetime.now(UTC) + timedelta(
        minutes=config.settings.JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES
    )

    payload = {
        "sub": email,
        "type": EMAIL_VERIFICATION_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        config.settings.JWT_SECRET_KEY,
        algorithm=config.settings.JWT_ALGORITHM,
    )


def create_password_reset_token(email: str) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=config.settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": email,
        "type": "password_reset",
        "iat": datetime.now(UTC),
        "exp": expire,
    }
    return jwt.encode(
        payload,
        config.settings.JWT_SECRET_KEY,
        algorithm=config.settings.JWT_ALGORITHM,
    )


def decode_email_verification_token(token: str) -> str:
    """Return the email bound to a valid verification token.

    Raises ``jwt.ExpiredSignatureError`` for expired tokens and
    ``jwt.InvalidTokenError`` for anything else (bad signature, wrong
    claim type, missing subject).
    """
    payload = jwt.decode(
        token,
        config.settings.JWT_SECRET_KEY,
        algorithms=[config.settings.JWT_ALGORITHM],
    )

    if payload.get("type") != EMAIL_VERIFICATION_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Not an email verification token")

    email = payload.get("sub")
    if not email:
        raise jwt.InvalidTokenError("Verification token missing subject")

    return email
