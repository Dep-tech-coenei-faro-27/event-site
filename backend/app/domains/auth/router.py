import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import (
    EmailDeliveryError,
    EmailSender,
    get_email_sender,
    mask_email,
)
from app.core.email.templates import (
    PASSWORD_CHANGED_SUBJECT,
    PASSWORD_RESET_SUBJECT,
    VERIFICATION_EMAIL_SUBJECT,
    build_password_changed_email_html,
    build_password_reset_email_html,
    build_verification_email_html,
)
from app.core.rate_limit import (
    RateLimit,
    client_ip,
    enforce_rate_limit,
    enforce_rate_limits,
)
from app.core.security import (
    ACCESS_COOKIE_NAME,
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_email_verification_token,
    decode_password_reset_token,
    password_fingerprint,
    verify_password,
)
from app.db.session import get_db
from app.domains.auth.dependencies import (
    EMAIL_VERIFICATION_REQUIRED_MESSAGE,
    AuthSession,
    decode_access_token,
    get_current_verified_session,
    get_current_verified_user,
)
from app.domains.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationEmailRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.domains.auth.service import (
    authenticate_user,
    get_password_reset_token,
    register_reset_token,
    revoke_token,
)
from app.domains.users.models import User
from app.domains.users.schemas import UserRead, UserRegister
from app.domains.users.service import (
    AccountAlreadyVerifiedError,
    ResetTokenUsedError,
    VerificationLinkOutdatedError,
    create_user,
    get_user_by_email,
    mark_user_verified,
    replace_unverified_user,
    reset_user_password,
    update_user_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

MIN_SESSION_AFTER_CHANGE = timedelta(minutes=1)

EMAIL_VERIFICATION_SENT_MESSAGE = (
    "If an account is awaiting verification, a verification email has been sent."
)


def _login_checks(email: str, ip: str) -> list[tuple[RateLimit, str]]:
    return [
        (RateLimit("login", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60), f"{email}|{ip}"),
        (
            RateLimit(
                "login-email", settings.RATE_LIMIT_LOGIN_PER_EMAIL_PER_MINUTE, 60
            ),
            email,
        ),
        (RateLimit("login-ip", settings.RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE, 60), ip),
    ]


def _email_checks(action: str, email: str, ip: str) -> list[tuple[RateLimit, str]]:
    return [
        (RateLimit(action, settings.RATE_LIMIT_EMAIL_PER_MINUTE, 60), email),
        (RateLimit(action, settings.RATE_LIMIT_EMAIL_PER_HOUR, 3600), email),
        (
            RateLimit(f"{action}-ip", settings.RATE_LIMIT_EMAIL_PER_IP_PER_MINUTE, 60),
            ip,
        ),
    ]


def _limit_token_attempts(db: Session, name: str, request: Request) -> None:
    rule = RateLimit(f"{name}-ip", settings.RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE, 60)
    enforce_rate_limit(db, (rule,), client_ip(request))


def _send_verification_email(email_sender: EmailSender, user: User) -> None:
    verification_token = create_email_verification_token(user.email, user.password_hash)
    verification_url = (
        f"{settings.FRONTEND_URL}{settings.FRONTEND_VERIFY_PATH}"
        f"?token={verification_token}"
    )
    html_body = build_verification_email_html(user.name, verification_url)
    try:
        email_sender.send_html(
            to_email=user.email,
            subject=VERIFICATION_EMAIL_SUBJECT,
            html_body=html_body,
        )
    except EmailDeliveryError as exc:
        logger.warning(
            "Failed to send verification email to %s: %s", mask_email(user.email), exc
        )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> UserRead:
    register_limit = RateLimit("register", settings.RATE_LIMIT_REGISTER_PER_MINUTE, 60)
    enforce_rate_limit(db, (register_limit,), client_ip(request))
    existing = get_user_by_email(db, payload.email)
    if existing is not None and existing.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    try:
        if existing is not None:
            user = replace_unverified_user(db, existing, payload)
        else:
            user = create_user(db, payload)
    except (IntegrityError, AccountAlreadyVerifiedError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from None
    _send_verification_email(email_sender, user)
    return UserRead.model_validate(user)


@router.post("/verify-email")
def verify_email(
    payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)
):
    _limit_token_attempts(db, "verify", request)
    try:
        email, fingerprint = decode_email_verification_token(payload.token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    user = get_user_by_email(db, email)
    if user is None or fingerprint != password_fingerprint(user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    if user.is_verified:
        return {"message": "Email verified successfully"}

    try:
        mark_user_verified(db, user)
    except VerificationLinkOutdatedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        ) from None
    return {"message": "Email verified successfully"}


@router.post("/resend-verification-email")
def resend_verification_email(
    payload: ResendVerificationEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    enforce_rate_limits(db, _email_checks("resend", payload.email, client_ip(request)))
    user = get_user_by_email(db, payload.email)

    if user is not None and not user.is_verified:
        _send_verification_email(email_sender, user)

    return {"message": EMAIL_VERIFICATION_SENT_MESSAGE}


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def get_current_user_info(
    current_user: User = Depends(get_current_verified_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    enforce_rate_limits(db, _login_checks(payload.email, client_ip(request)))
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_VERIFICATION_REQUIRED_MESSAGE,
        )

    if payload.remember_me:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES)
    else:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    _start_session(response, user, expires_delta)

    return {"message": "Login successful"}


def _start_session(response: Response, user: User, expires_delta: timedelta) -> None:
    token = create_access_token(user.id, user.token_version, expires_delta)
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=int(expires_delta.total_seconds()),
    )


@router.post("/logout")
def logout(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> dict[str, str]:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if token:
        try:
            claims = decode_access_token(token)
        except jwt.InvalidTokenError:
            claims = None
        if claims is not None:
            revoke_token(db, claims["jti"], datetime.fromtimestamp(claims["exp"], UTC))

    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"message": "Logout successful"}


@router.put("/password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    auth: AuthSession = Depends(get_current_verified_session),
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    current_user = auth.user
    change_limit = RateLimit(
        "password", settings.RATE_LIMIT_PASSWORD_CHANGE_PER_15_MINUTES, 900
    )
    enforce_rate_limit(db, (change_limit,), str(current_user.id))

    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your new password must be different from your current password",
        )

    update_user_password(db, current_user, payload.new_password)
    remaining = datetime.fromtimestamp(auth.payload["exp"], UTC) - datetime.now(UTC)
    _start_session(response, current_user, max(remaining, MIN_SESSION_AFTER_CHANGE))
    _send_password_changed_email(email_sender, current_user)

    return {"message": "Password changed successfully"}


def _send_password_changed_email(email_sender: EmailSender, user: User) -> None:
    try:
        email_sender.send_html(
            to_email=user.email,
            subject=PASSWORD_CHANGED_SUBJECT,
            html_body=build_password_changed_email_html(user.name),
        )
    except EmailDeliveryError as exc:
        logger.warning(
            "Failed to send password changed email to %s: %s",
            mask_email(user.email),
            exc,
        )


def _send_password_reset_email(
    db: Session, email_sender: EmailSender, user: User
) -> None:
    reset_token, jti, expire = create_password_reset_token(user.email)

    register_reset_token(db, user.id, jti, expire)

    reset_url = (
        f"{settings.FRONTEND_URL}{settings.FRONTEND_RESET_PATH}?token={reset_token}"
    )
    html_body = build_password_reset_email_html(user.name, reset_url)

    try:
        email_sender.send_html(
            to_email=user.email,
            subject=PASSWORD_RESET_SUBJECT,
            html_body=html_body,
        )
    except EmailDeliveryError as exc:
        logger.warning(
            "Failed to send password reset email to %s: %s", mask_email(user.email), exc
        )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    enforce_rate_limits(db, _email_checks("forgot", payload.email, client_ip(request)))
    user = get_user_by_email(db, payload.email)

    if user is not None:
        _send_password_reset_email(db, email_sender, user)

    return {
        "message": "If the email exists in our system, "
        "you will receive a password recovery link shortly."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    _limit_token_attempts(db, "reset", request)

    try:
        token_payload = decode_password_reset_token(payload.token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    email = token_payload.get("sub")
    jti = token_payload.get("jti")

    reset_token = get_password_reset_token(db, jti)

    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    if reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has already been used",
        )

    user = get_user_by_email(db, email)

    if user is None or not user.is_active or reset_token.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your new password must be different from your current password",
        )

    try:
        reset_user_password(db, user, payload.new_password, reset_token)
    except ResetTokenUsedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has already been used",
        ) from None
    _send_password_changed_email(email_sender, user)

    return {"message": "Password reset successfully"}
