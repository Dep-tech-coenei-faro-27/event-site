from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

import app.core.config as config

BCRYPT_MAX_PASSWORD_BYTES = 72
BCRYPT_ROUNDS = 12


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


def create_access_token(subject: str, role: str) -> str:

    issued_at = datetime.now(UTC)

    expire = datetime.now(UTC) + timedelta(
        minutes=config.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "role": role,
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        config.settings.JWT_SECRET_KEY,
        algorithm=config.settings.JWT_ALGORITHM,
    )
