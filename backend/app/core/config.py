import json
import re
import warnings
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

INSECURE_JWT_SECRETS = {"change-this-in-the-env-file", "ultra-secret-neei-key"}
MIN_JWT_SECRET_LENGTH = 32
PLACEHOLDER_SECRET_MARKER = "replace-me"
SECRET_HINT = 'python -c "import secrets; print(secrets.token_urlsafe(48))"'
ORIGIN_PATTERN = re.compile(r"^https?://[^/\s]+$")


class Settings(BaseSettings):
    # Um erro de configuração nunca imprime os valores recebidos (iam parar aos logs).
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), extra="ignore", hide_input_in_errors=True
    )

    PROJECT_NAME: str = "event-site-backend"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: Literal["dev", "prod"] = "prod"
    MEDIA_DIR: Path = BASE_DIR / "media"
    DEBUG: bool = False
    MAX_REQUEST_BYTES: int = Field(default=1_048_576, gt=0)

    CORS_ALLOW_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0, le=1440)
    JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES: int = Field(
        default=10080,  # 7 dias
        gt=0,
        le=43200,  # 30 dias
    )
    JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES: int = Field(default=30, gt=0, le=1440)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(default=15, gt=0, le=1440)
    FRONTEND_URL: str = "http://localhost:3000"
    FRONTEND_VERIFY_PATH: str = "/conta/verificar"
    FRONTEND_RESET_PATH: str = "/conta/redefinir"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_SENDER: str = ""
    SMTP_SECURITY: Literal["auto", "starttls", "ssl", "none"] = "auto"
    SMTP_TIMEOUT_SECONDS: int = Field(default=5, gt=0, le=60)

    UNVERIFIED_ACCOUNT_TTL_DAYS: int = Field(default=7, gt=0)

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    DATABASE_URL: str = ""

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_must_be_set(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                f"JWT_SECRET_KEY must be set. Generate one with: {SECRET_HINT}"
            )
        return value

    @field_validator("FRONTEND_URL")
    @classmethod
    def strip_frontend_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("FRONTEND_VERIFY_PATH", "FRONTEND_RESET_PATH")
    @classmethod
    def link_path_must_start_with_one_slash(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("must be a path starting with a single /")
        return value

    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            value = json.loads(text) if text.startswith("[") else text.split(",")
        if not isinstance(value, list):
            return value

        origins: list[str] = []
        for item in value:
            origin = str(item).strip().rstrip("/")
            if not origin:
                continue
            if origin in {"*", "null"}:
                raise ValueError(
                    f"CORS origin {origin!r} is not allowed: cookies are sent with "
                    "credentials, so every origin must be listed explicitly."
                )
            if not ORIGIN_PATTERN.match(origin):
                raise ValueError(
                    f"CORS origin {origin!r} must look like https://example.com"
                )
            origins.append(origin)
        return origins

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        self.DATABASE_URL = (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        return self

    @model_validator(mode="after")
    def check_environment(self) -> "Settings":
        weak_secret = (
            len(self.JWT_SECRET_KEY) < MIN_JWT_SECRET_LENGTH
            or self.JWT_SECRET_KEY in INSECURE_JWT_SECRETS
        )

        if self.ENVIRONMENT != "prod":
            if weak_secret:
                warnings.warn(
                    "JWT_SECRET_KEY is short or a known example value. This is "
                    "accepted in dev only. Generate a real one with: " + SECRET_HINT,
                    stacklevel=2,
                )
            return self

        problems: list[str] = []
        if weak_secret or PLACEHOLDER_SECRET_MARKER in self.JWT_SECRET_KEY:
            problems.append(
                f"JWT_SECRET_KEY must have at least {MIN_JWT_SECRET_LENGTH} "
                "characters and not be an example value. "
                f"Generate one with: {SECRET_HINT}"
            )
        if self.DEBUG:
            problems.append("DEBUG must be false (it leaks tracebacks in responses).")
        if self.POSTGRES_PASSWORD == "postgres":
            problems.append("POSTGRES_PASSWORD must not be the example value.")
        if not (self.SMTP_HOST and self.EMAIL_SENDER):
            problems.append("SMTP_HOST and EMAIL_SENDER must be set.")
        if self.SMTP_SECURITY == "none":
            problems.append("SMTP_SECURITY=none is not allowed in production.")
        if not self.FRONTEND_URL.startswith("https://"):
            problems.append("FRONTEND_URL must start with https://.")
        insecure = [o for o in self.CORS_ALLOW_ORIGINS if not o.startswith("https://")]
        if insecure:
            problems.append(f"CORS_ALLOW_ORIGINS must all be https:// ({insecure}).")

        if problems:
            raise ValueError(
                "Unsafe settings for ENVIRONMENT=prod:\n- " + "\n- ".join(problems)
            )
        return self


settings = Settings()
