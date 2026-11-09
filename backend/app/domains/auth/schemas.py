from pydantic import BaseModel, Field, field_validator

from app.core.security import validate_password
from app.core.validators import AsciiEmail


class LoginRequest(BaseModel):
    email: AsciiEmail
    password: str = Field(min_length=1, max_length=200)
    remember_me: bool = False


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2048)


class ResendVerificationEmailRequest(BaseModel):
    email: AsciiEmail


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)


class ForgotPasswordRequest(BaseModel):
    email: AsciiEmail


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2048)
    new_password: str = Field(min_length=8, max_length=200)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)
