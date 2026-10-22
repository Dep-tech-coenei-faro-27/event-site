import os

import pytest
from pydantic import ValidationError

from app.core.config import Settings

BASE = dict(
    ENVIRONMENT="prod",
    DEBUG=False,
    JWT_SECRET_KEY="a" * 40,
    QR_SECRET_KEY="b" * 40,
    POSTGRES_USER="u",
    POSTGRES_PASSWORD="strong-pass",
    POSTGRES_DB="d",
    POSTGRES_HOST="postgres",
    POSTGRES_PORT=5432,
    SMTP_HOST="smtp.resend.com",
    EMAIL_SENDER="noreply@x.pt",
    FRONTEND_URL="https://x.pt",
    CORS_ALLOW_ORIGINS="https://x.pt",
)
LIVE = dict(
    PAYMENTS_MODE="live",
    PAYMENTS_PROVIDER="ifthenpay",
    MBWAY_KEY="key",
    MBWAY_CALLBACK_KEY="c" * 32,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.upper() in Settings.model_fields:
            monkeypatch.delenv(name, raising=False)


def make(**over):
    return Settings(_env_file=None, **{**BASE, **over})


def test_default_is_off():
    assert make().PAYMENTS_MODE == "off"


def test_live_ok():
    assert make(**LIVE).PAYMENTS_MODE == "live"


@pytest.mark.parametrize("key", ["", "    ", "\t\n"])
def test_live_without_real_mbway_key_refuses(key):
    with pytest.raises(ValidationError, match="MBWAY_KEY"):
        make(**{**LIVE, "MBWAY_KEY": key})


def test_live_without_callback_key_refuses():
    with pytest.raises(ValidationError, match="MBWAY_CALLBACK_KEY"):
        make(**{**LIVE, "MBWAY_CALLBACK_KEY": ""})


def test_live_short_callback_key_refuses():
    with pytest.raises(ValidationError, match="at least 32"):
        make(**{**LIVE, "MBWAY_CALLBACK_KEY": "curta"})


def test_live_requires_https_base_url():
    with pytest.raises(ValidationError, match="https"):
        make(**LIVE, MBWAY_BASE_URL="http://x")


@pytest.mark.parametrize("mode", ["off", "live"])
def test_simulated_confirm_only_with_simulated(mode):
    extra = LIVE if mode == "live" else {}
    with pytest.raises(ValidationError, match="SIMULATED"):
        make(
            **{
                **extra,
                "PAYMENTS_MODE": mode,
                "PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS": 5,
            }
        )


def test_student_domains_parsed():
    s = make(STUDENT_EMAIL_DOMAINS=" Ualg.PT, alunos.ualg.pt. ")
    assert s.STUDENT_EMAIL_DOMAINS == ["ualg.pt", "alunos.ualg.pt"]


def test_empty_payment_rate_limit_fails_like_in_cd():
    with pytest.raises(ValidationError):
        make(RATE_LIMIT_PAYMENT_PER_MINUTE="")


def test_provider_secrets_are_stripped():
    s = make(
        PAYMENTS_MODE="live",
        PAYMENTS_PROVIDER="ifthenpay",
        MBWAY_KEY="  key  ",
        MBWAY_AUTH_TOKEN=" tok ",
        MBWAY_CALLBACK_KEY=" " + "c" * 32 + " ",
    )
    assert s.MBWAY_KEY == "key"
    assert s.MBWAY_AUTH_TOKEN == "tok"
    assert s.MBWAY_CALLBACK_KEY == "c" * 32
