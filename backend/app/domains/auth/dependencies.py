from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME, ACCESS_TOKEN_TYPE
from app.db.session import get_db
from app.domains.auth.service import is_token_revoked
from app.domains.users.enums import Role
from app.domains.users.models import User

EMAIL_VERIFICATION_REQUIRED_MESSAGE = "Please verify your email address to continue."
ADMIN_REQUIRED_MESSAGE = "Administrator access is required."
REQUIRED_CLAIMS = ["exp", "sub", "type", "jti", "tv"]


@dataclass
class AuthSession:
    user: User
    payload: dict


def decode_access_token(token: str) -> dict:
    """Return the claims of a valid access token, or raise ``jwt.InvalidTokenError``."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": REQUIRED_CLAIMS},
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_current_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    token = request.cookies.get(ACCESS_COOKIE_NAME)

    if not token:
        raise unauthorized("Not authenticated. Missing access token cookie.")

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token has expired.") from None
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token.") from None

    try:
        user_id = int(payload["sub"])
    except ValueError:
        raise unauthorized("Invalid token payload.") from None

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise unauthorized("User not found")

    if payload["tv"] != user.token_version or is_token_revoked(db, payload["jti"]):
        raise unauthorized("Token has been revoked.")

    if not user.is_active:
        raise unauthorized("Inactive user")

    # End the read so the connection goes back to the pool: this runs in a thread of
    # its own and the endpoint then waits for another one. Holding the connection
    # while waiting stalls the API when every thread is busy (a slow provider).
    db.commit()
    return AuthSession(user=user, payload=payload)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return get_current_session(request, db).user


def get_current_verified_session(
    request: Request, db: Session = Depends(get_db)
) -> AuthSession:
    session = get_current_session(request, db)

    if not session.user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_VERIFICATION_REQUIRED_MESSAGE,
        )

    return session


def get_current_verified_user(request: Request, db: Session = Depends(get_db)) -> User:
    return get_current_verified_session(request, db).user


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """The signed-in, verified user, only if their role is ``admin``.

    The role is read from the database on every request, never from the token, so
    promoting or demoting someone takes effect on their very next call.
    """
    user = get_current_verified_user(request, db)

    if user.role is not Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_REQUIRED_MESSAGE,
        )

    return user
