import pytest
from pydantic import ValidationError

from app.core.config import BASE_DIR, Settings

BASE = {
    "ENVIRONMENT": "dev",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "password",
    "POSTGRES_DB": "db",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": 5432,
    "JWT_SECRET_KEY": "k" * 40,
}

PROD = {
    **BASE,
    "ENVIRONMENT": "prod",
    "JWT_SECRET_KEY": "p" * 48,
    "SMTP_HOST": "smtp.example.com",
    "EMAIL_SENDER": "noreply@example.com",
    "FRONTEND_URL": "https://app.example.com",
    "CORS_ALLOW_ORIGINS": ["https://app.example.com"],
}


def make(**overrides) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})


def make_prod(**overrides) -> Settings:
    return Settings(_env_file=None, **{**PROD, **overrides})


def test_jwt_secret_is_required(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    values = {k: v for k, v in BASE.items() if k != "JWT_SECRET_KEY"}

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_blank_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be set"):
        make(JWT_SECRET_KEY="   ")


def test_dev_accepts_a_short_secret_but_warns():
    with pytest.warns(UserWarning, match="JWT_SECRET_KEY"):
        settings = make(JWT_SECRET_KEY="short-dev-key")

    assert settings.ENVIRONMENT == "dev"


@pytest.mark.parametrize("secret", ["too-short", "ultra-secret-neei-key"])
def test_prod_rejects_short_and_example_secrets(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        make_prod(JWT_SECRET_KEY=secret)


def test_prod_with_safe_settings_loads():
    settings = make_prod()

    assert settings.ENVIRONMENT == "prod"
    assert settings.DEBUG is False


def test_prod_rejects_debug():
    with pytest.raises(ValidationError, match="DEBUG"):
        make_prod(DEBUG=True)


def test_prod_requires_smtp_settings():
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        make_prod(SMTP_HOST="")


def test_prod_requires_https_urls():
    with pytest.raises(ValidationError, match="FRONTEND_URL"):
        make_prod(FRONTEND_URL="http://app.example.com")
    with pytest.raises(ValidationError, match="CORS_ALLOW_ORIGINS"):
        make_prod(CORS_ALLOW_ORIGINS=["http://app.example.com"])


def test_prod_reports_every_problem_at_once():
    with pytest.raises(ValidationError) as error:
        make_prod(DEBUG=True, SMTP_HOST="", JWT_SECRET_KEY="short")

    message = str(error.value)
    assert "DEBUG" in message
    assert "SMTP_HOST" in message
    assert "JWT_SECRET_KEY" in message


@pytest.mark.parametrize("algorithm", ["none", "RS256", "bogus"])
def test_only_hmac_algorithms_are_accepted(algorithm):
    with pytest.raises(ValidationError):
        make(JWT_ALGORITHM=algorithm)


@pytest.mark.parametrize(
    "name", ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES"]
)
@pytest.mark.parametrize("minutes", [0, -5, 100000])
def test_token_lifetimes_must_be_positive_and_capped(name, minutes):
    with pytest.raises(ValidationError):
        make(**{name: minutes})


def test_remember_me_lifetime_is_capped_at_30_days():
    assert make(JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES=43200)
    with pytest.raises(ValidationError):
        make(JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES=43201)


def test_cors_accepts_a_list_and_removes_trailing_slashes():
    settings = make(CORS_ALLOW_ORIGINS=["https://enei.pt/", "https://www.enei.pt"])

    assert settings.CORS_ALLOW_ORIGINS == ["https://enei.pt", "https://www.enei.pt"]


def test_cors_accepts_comma_separated_text():
    settings = make(CORS_ALLOW_ORIGINS="https://a.example.com, https://b.example.com/")

    assert settings.CORS_ALLOW_ORIGINS == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_cors_accepts_a_json_list_as_text():
    settings = make(CORS_ALLOW_ORIGINS='["https://a.example.com"]')

    assert settings.CORS_ALLOW_ORIGINS == ["https://a.example.com"]


def test_cors_reads_a_comma_separated_environment_variable(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS", "https://a.example.com,https://b.example.com"
    )

    settings = Settings(_env_file=None, **BASE)

    assert settings.CORS_ALLOW_ORIGINS == [
        "https://a.example.com",
        "https://b.example.com",
    ]


@pytest.mark.parametrize("origin", ["*", "null"])
def test_cors_rejects_wildcard_and_null_origins(origin):
    with pytest.raises(ValidationError, match="not allowed"):
        make(CORS_ALLOW_ORIGINS=[origin])


@pytest.mark.parametrize(
    "origin", ["localhost:3000", "ftp://example.com", "https://a.com/path"]
)
def test_cors_rejects_malformed_origins(origin):
    with pytest.raises(ValidationError, match="must look like"):
        make(CORS_ALLOW_ORIGINS=[origin])


def test_prod_rejects_the_secret_in_env_example():
    lines = (BASE_DIR / ".env.example").read_text().splitlines()
    example = next(
        line.split("=", 1)[1] for line in lines if line.startswith("JWT_SECRET_KEY=")
    )

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        make_prod(JWT_SECRET_KEY=example)


def test_a_configuration_error_never_prints_the_values_it_received():
    secret = "OnlyForThisTest-" + "z" * 40

    with pytest.raises(ValidationError) as error:
        make_prod(DEBUG=True, JWT_SECRET_KEY=secret, POSTGRES_PASSWORD=secret)

    assert secret not in str(error.value)
    assert "input_value" not in str(error.value)
