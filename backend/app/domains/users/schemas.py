from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password
from app.core.validators import AsciiEmail, validate_name
from app.domains.users.models import Role, StudentVerificationStatus


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: AsciiEmail
    password: str = Field(min_length=8, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password(value)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    is_verified: bool
    student_verification_status: StudentVerificationStatus
