from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2048)


class ResendVerificationEmailRequest(BaseModel):
    email: EmailStr
