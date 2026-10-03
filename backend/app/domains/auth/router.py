import logging
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailDeliveryError, EmailSender, get_email_sender
from app.core.email.templates import (
    PASSWORD_RESET_SUBJECT,
    VERIFICATION_EMAIL_SUBJECT,
    build_password_reset_email_html,
    build_verification_email_html,
)
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_email_verification_token,
    verify_password,
)
from app.db.session import get_db
from app.domains.auth.dependencies import (
    EMAIL_VERIFICATION_REQUIRED_MESSAGE,
    get_current_verified_user,
)
from app.domains.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationEmailRequest,
    VerifyEmailRequest,
)
from app.domains.auth.service import authenticate_user
from app.domains.users.models import User
from app.domains.users.schemas import UserRead, UserRegister
from app.domains.users.service import (
    create_user,
    get_user_by_email,
    mark_user_verified,
    update_user_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

EMAIL_ALREADY_VERIFIED_MESSAGE = "Email already verified"
EMAIL_VERIFICATION_SENT_MESSAGE = (
    "If an account is awaiting verification, a verification email has been sent."
)


def _send_verification_email(email_sender: EmailSender, user: User) -> None:
    verification_token = create_email_verification_token(user.email)
    verification_url = (
        f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    )
    html_body = build_verification_email_html(user.name, verification_url)
    try:
        email_sender.send_html(
            to_email=user.email,
            subject=VERIFICATION_EMAIL_SUBJECT,
            html_body=html_body,
        )
    except EmailDeliveryError as exc:
        logger.warning("Failed to send verification email to %s: %s", user.email, exc)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> UserRead:
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    try:
        user = create_user(db, payload)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from None
    _send_verification_email(email_sender, user)
    return UserRead.model_validate(user)


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    try:
        email = decode_email_verification_token(payload.token)
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
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    if user.is_verified:
        return {"message": "Email verified successfully"}

    mark_user_verified(db, user)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification-email")
def resend_verification_email(
    payload: ResendVerificationEmailRequest,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    user = get_user_by_email(db, payload.email)

    if user is not None and user.is_verified:
        return {"message": EMAIL_ALREADY_VERIFIED_MESSAGE}

    if user is not None:
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
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
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
        max_age = 60 * settings.JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES)
    else:
        max_age = 60 * settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    token = create_access_token(
        subject=user.email, role=user.role.value, expires_delta=expires_delta
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
    )

    return {"message": "Login successful"}


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"message": "Logout successful"}


@router.put("/password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):

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

    return {"message": "Password changed successfully"}


def _send_password_reset_email(email_sender: EmailSender, user: User) -> None:
    reset_token = create_password_reset_token(user.email)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    html_body = build_password_reset_email_html(user.name, reset_url)

    try:
        email_sender.send_html(
            to_email=user.email,
            subject=PASSWORD_RESET_SUBJECT,
            html_body=html_body,
        )
    except EmailDeliveryError as exc:
        logger.warning("Failed to send password reset email to %s: %s", user.email, exc)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    user = get_user_by_email(db, payload.email)

    if user is not None:
        _send_password_reset_email(email_sender, user)

    return {
        "message": "If the email exists in our system, "
        "you will receive a password recovery link shortly."
    }
