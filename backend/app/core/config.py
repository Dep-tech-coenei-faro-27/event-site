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
    QR_SECRET_KEY: str = ""
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
    # Emails go to the email_outbox table and a worker sends them (and retries).
    EMAIL_OUTBOX_WORKER: bool = True
    EMAIL_OUTBOX_POLL_SECONDS: int = Field(default=5, gt=0, le=300)
    EMAIL_OUTBOX_MAX_ATTEMPTS: int = Field(default=10, gt=0, le=30)

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = Field(default=5, gt=0)
    RATE_LIMIT_LOGIN_PER_EMAIL_PER_MINUTE: int = Field(default=20, gt=0)
    RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE: int = Field(default=30, gt=0)
    RATE_LIMIT_REGISTER_PER_MINUTE: int = Field(default=2, gt=0)
    RATE_LIMIT_EMAIL_PER_MINUTE: int = Field(default=1, gt=0)
    RATE_LIMIT_EMAIL_PER_HOUR: int = Field(default=5, gt=0)
    RATE_LIMIT_EMAIL_PER_IP_PER_MINUTE: int = Field(default=10, gt=0)
    RATE_LIMIT_PASSWORD_CHANGE_PER_15_MINUTES: int = Field(default=2, gt=0)
    RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE: int = Field(default=20, gt=0)
    RATE_LIMIT_PAYMENT_PER_MINUTE: int = Field(default=10, gt=0)
    RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE: int = Field(default=120, gt=0)
    RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE: int = Field(default=60, gt=0)

    UNVERIFIED_ACCOUNT_TTL_DAYS: int = Field(default=7, gt=0)

    # Institutional email domains that grant the student status automatically.
    STUDENT_EMAIL_DOMAINS: Annotated[list[str], NoDecode] = []

    # Ticket prices live in the database (ticket_tiers.price_cents) and are changed
    # at runtime with `python -m app.domains.payments.set_price`. A NULL price means
    # the ticket office is still closed and /payment/initiate answers 503.

    # off: no payments at all (default). simulated: fake provider so the frontend
    # can integrate. live: real ifthenpay gateway, needs the provider credentials.
    PAYMENTS_MODE: Literal["off", "simulated", "live"] = "off"
    MBWAY_KEY: str = ""
    MBWAY_BASE_URL: str = "https://api.ifthenpay.com/spg/payment/mbway"
    MBWAY_AUTH_TOKEN: str = ""
    # Anti-phishing key ifthenpay echoes back on the payment callback. Required when
    # PAYMENTS_MODE=live: without it we cannot trust a callback.
    MBWAY_CALLBACK_KEY: str = ""
    MBWAY_TIMEOUT_SECONDS: int = Field(default=10, gt=0, le=60)
    MBWAY_PAYMENT_TIMEOUT_SECONDS: int = Field(default=240, gt=0, le=900)
    # Staging only: with a positive value the simulated provider starts confirming
    # payments a few seconds after they are created, so the ticket/QR/email flow can
    # be exercised without ifthenpay. Only allowed with PAYMENTS_MODE=simulated; the
    # backend refuses to start with `live` or `off` and a positive value.
    PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS: int = Field(default=0, ge=0, le=3600)

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

    @field_validator("STUDENT_EMAIL_DOMAINS", mode="before")
    @classmethod
    def parse_student_domains(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            value = json.loads(text) if text.startswith("[") else text.split(",")
        if not isinstance(value, list):
            return value

        domains: list[str] = []
        for item in value:
            domain = str(item).strip().lower().rstrip(".")
            if not domain:
                continue
            if "@" in domain or "/" in domain or any(char.isspace() for char in domain):
                raise ValueError(
                    f"Student email domain {domain!r} must look like "
                    "student.example.edu"
                )
            domains.append(domain)
        return domains

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
        weak_qr_secret = (
            not self.QR_SECRET_KEY.strip()
            or len(self.QR_SECRET_KEY) < MIN_JWT_SECRET_LENGTH
            or self.QR_SECRET_KEY in INSECURE_JWT_SECRETS
        )

        if self.PAYMENTS_MODE == "live":
            if not self.MBWAY_KEY:
                raise ValueError("PAYMENTS_MODE=live requires MBWAY_KEY to be set.")
            if not self.MBWAY_BASE_URL.startswith("https://"):
                raise ValueError(
                    "PAYMENTS_MODE=live requires MBWAY_BASE_URL to start with https://."
                )
            if not self.MBWAY_CALLBACK_KEY:
                raise ValueError(
                    "PAYMENTS_MODE=live requires MBWAY_CALLBACK_KEY to be set "
                    "(the ifthenpay anti-phishing key)."
                )
            if len(self.MBWAY_CALLBACK_KEY) < MIN_JWT_SECRET_LENGTH:
                raise ValueError(
                    "PAYMENTS_MODE=live requires MBWAY_CALLBACK_KEY to be at least "
                    f"{MIN_JWT_SECRET_LENGTH} characters (the ifthenpay anti-phishing "
                    "key)."
                )

        if (
            self.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS > 0
            and self.PAYMENTS_MODE != "simulated"
        ):
            raise ValueError(
                "PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS requires "
                "PAYMENTS_MODE=simulated; the confirming simulator cannot run with "
                "live or off payments."
            )

        if self.ENVIRONMENT != "prod":
            if weak_secret:
                warnings.warn(
                    "JWT_SECRET_KEY is short or a known example value. This is "
                    "accepted in dev only. Generate a real one with: " + SECRET_HINT,
                    stacklevel=2,
                )
            if not self.QR_SECRET_KEY.strip():
                self.QR_SECRET_KEY = f"dev-qr-{self.JWT_SECRET_KEY}"
            elif weak_qr_secret:
                warnings.warn(
                    "QR_SECRET_KEY is short or a known example value. This is "
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
        if (
            weak_qr_secret
            or PLACEHOLDER_SECRET_MARKER in self.QR_SECRET_KEY
            or self.QR_SECRET_KEY == self.JWT_SECRET_KEY
        ):
            problems.append(
                f"QR_SECRET_KEY must have at least {MIN_JWT_SECRET_LENGTH} "
                "characters, not be an example value, and differ from JWT_SECRET_KEY. "
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
