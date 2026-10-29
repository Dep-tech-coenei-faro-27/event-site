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


def stripe_key_mode(key: str) -> str:
    """``test`` for a sandbox key, ``live`` for a real one, ``unknown`` otherwise."""
    if key.startswith(("sk_test_", "rk_test_")):
        return "test"
    if key.startswith(("sk_live_", "rk_live_")):
        return "live"
    return "unknown"


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
    # Emails the first server may send per UTC day (0: only its own refusal counts).
    SMTP_DAILY_LIMIT: int = Field(default=0, ge=0)
    # A second SMTP server, used when the first is over its quota or failing.
    SMTP2_HOST: str = ""
    SMTP2_PORT: int = 587
    SMTP2_USER: str = ""
    SMTP2_PASSWORD: str = ""
    SMTP2_SECURITY: Literal["auto", "starttls", "ssl", "none"] = "auto"
    # The sender on the second server; empty uses EMAIL_SENDER.
    SMTP2_EMAIL_SENDER: str = ""
    # Emails go to the email_outbox table and a worker sends them (and retries).
    EMAIL_OUTBOX_WORKER: bool = True
    EMAIL_OUTBOX_POLL_SECONDS: int = Field(default=5, gt=0, le=300)
    EMAIL_OUTBOX_MAX_ATTEMPTS: int = Field(default=10, gt=0, le=30)

    # Pool of database connections. The server answers the sync endpoints in a pool of
    # 40 threads (anyio's default) and each holds one connection for its whole request,
    # so the pool must not be smaller than that: with fewer connections than threads,
    # threads queue for a connection while others cannot finish, and the whole API
    # stalls until the timeout (measured: 300 payments started in 10 s stopped the
    # server for 30 s). A short timeout makes an overload fail fast, not hang. The
    # threads that start payments (PAYMENT_INITIATE_THREADS) are not counted: they only
    # hold a connection for short reads and writes, never while the provider answers
    # (scripts/loadtest/RESULTADOS.md: 300 payments at 9 s each used 13 connections).
    DB_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    DB_POOL_TIMEOUT: float = Field(default=10, gt=0, le=60)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = Field(default=5, gt=0)
    RATE_LIMIT_LOGIN_PER_EMAIL_PER_MINUTE: int = Field(default=20, gt=0)
    # Per IP, everyone behind one address counts together (a campus, the venue). Each
    # attempt costs ~0.2-0.3 s of bcrypt, so 300 a minute from one IP take ~1 core of
    # the 2 vCPU server (scripts/loadtest/RESULTADOS.md): the default stays at 60 and
    # the Variable RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE raises it on the day if needed.
    RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE: int = Field(default=60, gt=0)
    RATE_LIMIT_REGISTER_PER_MINUTE: int = Field(default=2, gt=0)
    RATE_LIMIT_EMAIL_PER_MINUTE: int = Field(default=1, gt=0)
    RATE_LIMIT_EMAIL_PER_HOUR: int = Field(default=5, gt=0)
    RATE_LIMIT_EMAIL_PER_IP_PER_MINUTE: int = Field(default=10, gt=0)
    RATE_LIMIT_PASSWORD_CHANGE_PER_15_MINUTES: int = Field(default=2, gt=0)
    RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE: int = Field(default=20, gt=0)
    RATE_LIMIT_PAYMENT_PER_MINUTE: int = Field(default=10, gt=0)
    RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE: int = Field(default=120, gt=0)
    RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE: int = Field(default=60, gt=0)
    # The shop page of that same campus; one read costs ~10 ms (scripts/loadtest).
    RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE: int = Field(default=600, gt=0)
    RATE_LIMIT_STUDENT_PROOF_PER_HOUR: int = Field(default=5, gt=0)
    RATE_LIMIT_STUDENT_PROOF_PER_IP_PER_HOUR: int = Field(default=20, gt=0)

    UNVERIFIED_ACCOUNT_TTL_DAYS: int = Field(default=7, gt=0)

    # Institutional email domains that grant the student status automatically.
    STUDENT_EMAIL_DOMAINS: Annotated[list[str], NoDecode] = []

    # Proof of enrolment for students without an institutional email. The files wait
    # here for a decision (then are deleted). This folder must be a private volume,
    # never inside MEDIA_DIR, which is served to the internet.
    STUDENT_PROOF_DIR: Path = BASE_DIR / "private" / "student-proofs"
    STUDENT_PROOF_MAX_BYTES: int = Field(default=1_048_576, gt=0, le=10_485_760)
    # PEM bundle of the certificates of the qualified trust services of the EU
    # trusted lists (made by `python -m app.domains.students.trust_list`). Empty uses
    # the snapshot that ships with the code.
    STUDENT_TRUST_ANCHORS_FILE: Path | None = None

    # Seats for sale on the site, ONE number for every modality together (there is no
    # stock per modality). Tickets of the organisation and of guests are not sold here
    # and do not count. Paid payments and the ones still waiting take a seat.
    TICKET_STOCK_LIMIT: int = Field(default=600, ge=0)

    # Ticket prices live in the database (ticket_tiers.price_cents) and are changed
    # at runtime with `python -m app.domains.payments.set_price`. A NULL price means
    # the ticket office is still closed and /payment/initiate answers 503.

    # off: no payments at all (default). simulated: fake provider so the frontend
    # can integrate. live: the real gateway chosen by PAYMENTS_PROVIDER, which needs
    # that provider's credentials.
    PAYMENTS_MODE: Literal["off", "simulated", "live"] = "off"
    PAYMENTS_PROVIDER: Literal["stripe", "ifthenpay"] = "stripe"
    # Stripe MB WAY (PaymentIntents API). A sandbox key starts with sk_test_, a real
    # one with sk_live_; a restricted key (rk_) works too.
    STRIPE_SECRET_KEY: str = ""
    # A sandbox key (sk_test_...) in ENVIRONMENT=prod is refused unless this is on: the
    # sandbox approves any phone number, so a production server left on a test key
    # would hand out tickets without charging anyone. Only the staging turns it on.
    STRIPE_ALLOW_TEST_KEY: bool = False
    STRIPE_API_VERSION: str = "2026-08-26.dahlia"
    # Signing secret of the webhook endpoint (whsec_...), shown once the endpoint is
    # registered in the Stripe dashboard (or by `stripe listen` in development).
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_WEBHOOK_TOLERANCE_SECONDS: int = Field(default=300, gt=0, le=3600)
    MBWAY_KEY: str = ""
    MBWAY_BASE_URL: str = "https://api.ifthenpay.com/spg/payment/mbway"
    MBWAY_AUTH_TOKEN: str = ""
    # Anti-phishing key ifthenpay echoes back on the payment callback. Required when
    # PAYMENTS_MODE=live: without it we cannot trust a callback.
    MBWAY_CALLBACK_KEY: str = ""
    MBWAY_TIMEOUT_SECONDS: int = Field(default=10, gt=0, le=60)
    MBWAY_PAYMENT_TIMEOUT_SECONDS: int = Field(default=240, gt=0, le=900)
    # A payment keeps its seat while the provider says it is waiting. When the provider
    # cannot say (it answers something we do not understand, or we never saved its
    # reference), the seat is released this long after the payment deadline.
    MBWAY_UNRESOLVED_MAX_WAIT_SECONDS: int = Field(default=1800, gt=0, le=86400)
    # Stripe ends an MB WAY wait by itself. If a Stripe payment is still waiting this
    # long after its deadline, we cancel the PaymentIntent so that it frees its seat
    # and can no longer be approved. Keep it above the window Stripe really gives.
    STRIPE_CANCEL_GRACE_SECONDS: int = Field(default=120, ge=0, le=900)
    # The status poll asks the provider about a payment at most this often (0 = every
    # time). Many people polling every 2 seconds must not become as many calls to the
    # provider; the callback still confirms a payment at once.
    PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS: int = Field(default=5, ge=0, le=300)
    # Threads that start payments (each waits on the provider). Separate from the 40
    # that answer every other request, so a slow provider only slows down purchases:
    # measured at 9 s per call, sharing them stalled the whole API (scripts/loadtest).
    PAYMENT_INITIATE_THREADS: int = Field(default=40, ge=1, le=200)
    # Live payment status (Server-Sent Events): the heartbeat keeps proxies from closing
    # a quiet stream, how long one stream lives (the browser reconnects), streams per
    # person, and how often the provider is asked about the payments being waited for.
    PAYMENT_EVENTS_HEARTBEAT_SECONDS: float = Field(default=15, gt=0, le=60)
    PAYMENT_EVENTS_MAX_SECONDS: float = Field(default=600, gt=0, le=3600)
    PAYMENT_EVENTS_MAX_PER_USER: int = Field(default=3, ge=0, le=20)
    PAYMENT_EVENTS_RECONCILE_SECONDS: float = Field(default=5, gt=0, le=60)
    # Staging only: with a positive value the simulated provider starts confirming
    # payments a few seconds after they are created, so the ticket/QR/email flow can
    # be exercised without ifthenpay. Only allowed with PAYMENTS_MODE=simulated; the
    # backend refuses to start with `live` or `off` and a positive value.
    PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS: int = Field(default=0, ge=0, le=3600)
    # Load tests only: the simulated provider takes this long to answer each call, like
    # a slow ifthenpay. Past MBWAY_TIMEOUT_SECONDS it gives up as the real client would
    # (a gateway error after the timeout). Only allowed with PAYMENTS_MODE=simulated.
    PAYMENTS_SIMULATED_LATENCY_SECONDS: float = Field(default=0, ge=0, le=60)

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

    @field_validator(
        "MBWAY_KEY",
        "MBWAY_AUTH_TOKEN",
        "MBWAY_CALLBACK_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
    )
    @classmethod
    def strip_provider_secrets(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def keep_student_proofs_private(self) -> "Settings":
        proofs = self.STUDENT_PROOF_DIR.resolve()
        media = self.MEDIA_DIR.resolve()
        if proofs == media or media in proofs.parents:
            raise ValueError(
                "STUDENT_PROOF_DIR must be outside MEDIA_DIR, which is public"
            )
        return self

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

        if self.PAYMENTS_MODE == "live" and self.PAYMENTS_PROVIDER == "stripe":
            if not self.STRIPE_SECRET_KEY.startswith(("sk_", "rk_")):
                raise ValueError(
                    "PAYMENTS_MODE=live with PAYMENTS_PROVIDER=stripe requires "
                    "STRIPE_SECRET_KEY to be a Stripe secret key (sk_...)."
                )
            if not self.STRIPE_WEBHOOK_SECRET.startswith("whsec_"):
                raise ValueError(
                    "PAYMENTS_MODE=live with PAYMENTS_PROVIDER=stripe requires "
                    "STRIPE_WEBHOOK_SECRET to be the endpoint signing secret "
                    "(whsec_...)."
                )
            if (
                self.ENVIRONMENT == "prod"
                and stripe_key_mode(self.STRIPE_SECRET_KEY) == "test"
                and not self.STRIPE_ALLOW_TEST_KEY
            ):
                raise ValueError(
                    "STRIPE_SECRET_KEY is a Stripe test key (sk_test_...) in "
                    "production: the sandbox approves any phone number, so nobody "
                    "would be charged. Use the live key, or set "
                    "STRIPE_ALLOW_TEST_KEY=true on a staging server."
                )

        if self.PAYMENTS_MODE == "live" and self.PAYMENTS_PROVIDER == "ifthenpay":
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
        if (
            self.PAYMENTS_SIMULATED_LATENCY_SECONDS > 0
            and self.PAYMENTS_MODE != "simulated"
        ):
            raise ValueError(
                "PAYMENTS_SIMULATED_LATENCY_SECONDS requires PAYMENTS_MODE=simulated."
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
        if self.SMTP2_HOST and self.SMTP2_SECURITY == "none":
            problems.append("SMTP2_SECURITY=none is not allowed in production.")
        if self.SMTP2_HOST and not (self.SMTP2_USER and self.SMTP2_PASSWORD):
            # Otherwise the mistake only shows when the primary runs out, on the
            # busiest day.
            problems.append(
                "SMTP2_USER and SMTP2_PASSWORD must be set when SMTP2_HOST is."
            )
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
