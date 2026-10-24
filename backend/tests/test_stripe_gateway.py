import base64
import io
import json
from urllib import error

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings, stripe_key_mode
from app.domains.payments import gateway as gateway_module
from app.domains.payments.gateway import (
    PaymentGatewayError,
    StripeMBWayGateway,
    UnrecognisedStatusError,
    get_mbway_gateway,
)
from app.domains.payments.models import TransactionStatus

SECRET = "sk_test_" + "a" * 40
INTENT = "pi_3USkViKnHPoxsDHG1o4JvnxP"
REFERENCE = "ENEI-0000000001"


def build_gateway(response=None):
    calls: list[tuple] = []

    def fake_request(method, url, form, headers):
        calls.append((method, url, form, headers))
        return response

    gateway = StripeMBWayGateway(
        secret_key=SECRET,
        timeout_seconds=10,
        api_version="2026-08-26.dahlia",
        http_request=fake_request,
    )
    return gateway, calls


def intent(status, *, code=None, reference=REFERENCE, **extra):
    data = {"id": INTENT, "status": status, "metadata": {"reference": reference}}
    if code:
        data["last_payment_error"] = {"code": code, "type": "card_error"}
    return {**data, **extra}


def test_create_confirms_a_mb_way_payment_intent_with_the_phone_from_our_form():
    gateway, calls = build_gateway(intent("requires_action"))

    payment = gateway.create_payment(
        reference=REFERENCE,
        amount_cents=2500,
        phone="912345678",
        email="ana@example.com",
    )

    assert payment.provider_reference == INTENT
    assert payment.status is TransactionStatus.PENDING
    method, url, form, headers = calls[0]
    assert (method, url) == ("POST", "https://api.stripe.com/v1/payment_intents")
    assert form == {
        "amount": "2500",
        "currency": "eur",
        "payment_method_types[]": "mb_way",
        "payment_method_data[type]": "mb_way",
        "payment_method_data[billing_details][phone]": "+351912345678",
        "confirm": "true",
        "metadata[reference]": REFERENCE,
    }
    # The person's email stays with us: Stripe only needs the phone.
    assert "ana@example.com" not in json.dumps(form)


def test_create_is_idempotent_per_payment_and_pins_the_api_version():
    gateway, calls = build_gateway(intent("requires_action"))

    gateway.create_payment(
        reference=REFERENCE, amount_cents=800, phone="912345678", email="a@b.pt"
    )

    headers = calls[0][3]
    assert headers["Idempotency-Key"] == f"enei-{REFERENCE}"
    assert headers["Stripe-Version"] == "2026-08-26.dahlia"
    token = base64.b64decode(headers["Authorization"].removeprefix("Basic ")).decode()
    assert token == f"{SECRET}:"


@pytest.mark.parametrize(
    "answer",
    [{}, {"id": None}, {"id": "ch_123"}, {"id": "pi_1/../account"}, {"id": ""}],
)
def test_create_without_a_usable_payment_intent_id_fails(answer):
    gateway, _ = build_gateway(answer)

    with pytest.raises(PaymentGatewayError, match="PaymentIntent id"):
        gateway.create_payment(
            reference=REFERENCE, amount_cents=800, phone="912345678", email="a@b.pt"
        )


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (intent("succeeded"), TransactionStatus.CONFIRMED),
        (intent("requires_action"), TransactionStatus.PENDING),
        (intent("processing"), TransactionStatus.PENDING),
        (intent("requires_confirmation"), TransactionStatus.PENDING),
        (intent("canceled"), TransactionStatus.FAILED),
        (
            intent(
                "requires_payment_method",
                code="payment_intent_payment_attempt_expired",
            ),
            TransactionStatus.EXPIRED,
        ),
        (
            intent("requires_payment_method", code="payment_method_customer_decline"),
            TransactionStatus.FAILED,
        ),
        (
            intent("requires_payment_method", code="payment_method_provider_decline"),
            TransactionStatus.FAILED,
        ),
        (
            intent("requires_payment_method", code="payment_method_not_available"),
            TransactionStatus.FAILED,
        ),
    ],
)
def test_status_query_maps_the_payment_intent_states(answer, expected):
    gateway, calls = build_gateway(answer)

    assert (
        gateway.get_status(reference=REFERENCE, provider_reference=INTENT) == expected
    )
    assert calls[0][:2] == (
        "GET",
        f"https://api.stripe.com/v1/payment_intents/{INTENT}",
    )
    assert calls[0][2] is None


@pytest.mark.parametrize(
    "answer",
    [
        intent("requires_payment_method"),  # never confirmed: no reason to call it over
        intent("requires_capture"),
        intent("something_new"),
        {"id": INTENT, "metadata": {"reference": REFERENCE}},
    ],
)
def test_an_unreadable_status_is_an_error_and_not_a_wait(answer, caplog):
    gateway, _ = build_gateway(answer)

    with pytest.raises(UnrecognisedStatusError):
        gateway.get_status(reference=REFERENCE, provider_reference=INTENT)
    assert "unrecognised status" in caplog.text


def test_status_query_without_a_provider_reference_stays_pending_and_does_not_call():
    gateway, calls = build_gateway(intent("succeeded"))

    status = gateway.get_status(reference=REFERENCE, provider_reference=None)

    assert status is TransactionStatus.PENDING
    assert calls == []


@pytest.mark.parametrize("bad", ["ch_123", "pi_1/../account", "pi_1?x=1", "pi_"])
def test_status_query_never_builds_a_url_from_a_foreign_reference(bad):
    gateway, calls = build_gateway(intent("succeeded"))

    with pytest.raises(PaymentGatewayError):
        gateway.get_status(reference=REFERENCE, provider_reference=bad)
    assert calls == []


def test_status_of_another_payments_intent_is_never_read():
    gateway, _ = build_gateway(intent("succeeded", reference="ENEI-0000000099"))

    with pytest.raises(PaymentGatewayError, match="does not belong"):
        gateway.get_status(reference=REFERENCE, provider_reference=INTENT)


def http_error(code, body):
    return error.HTTPError("https://api.stripe.com", code, "x", {}, io.BytesIO(body))


def real_gateway():
    return StripeMBWayGateway(
        secret_key=SECRET, timeout_seconds=3, api_version="2026-08-26.dahlia"
    )


def test_a_stripe_error_keeps_the_code_and_message_but_never_the_key(monkeypatch):
    body = json.dumps(
        {
            "error": {
                "type": "invalid_request_error",
                "code": "phone_number_invalid",
                "message": "Invalid phone number.",
            }
        }
    ).encode()

    def refuse(req, timeout):
        raise http_error(400, body)

    monkeypatch.setattr(gateway_module.request, "urlopen", refuse)

    with pytest.raises(PaymentGatewayError) as raised:
        real_gateway().create_payment(
            reference=REFERENCE, amount_cents=800, phone="912345678", email="a@b.pt"
        )
    message = str(raised.value)
    assert "400" in message and "phone_number_invalid" in message
    assert "Invalid phone number." in message
    assert SECRET not in message and "912345678" not in message


def test_an_error_page_that_is_not_json_still_fails_cleanly(monkeypatch):
    def refuse(req, timeout):
        raise http_error(502, b"<html>Bad gateway</html>")

    monkeypatch.setattr(gateway_module.request, "urlopen", refuse)

    with pytest.raises(PaymentGatewayError, match="HTTP 502"):
        real_gateway().get_status(reference=REFERENCE, provider_reference=INTENT)


def test_a_network_failure_is_a_gateway_error(monkeypatch):
    def down(req, timeout):
        raise error.URLError("timed out")

    monkeypatch.setattr(gateway_module.request, "urlopen", down)

    with pytest.raises(PaymentGatewayError, match="unreachable"):
        real_gateway().get_status(reference=REFERENCE, provider_reference=INTENT)


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]"])
def test_an_unreadable_answer_is_a_gateway_error(monkeypatch, body):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return body

    monkeypatch.setattr(
        gateway_module.request, "urlopen", lambda req, timeout: Response()
    )

    with pytest.raises(PaymentGatewayError):
        real_gateway().get_status(reference=REFERENCE, provider_reference=INTENT)


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


WEBHOOK = dict(STRIPE_WEBHOOK_SECRET="whsec_" + "w" * 32)


def make(**over):
    return Settings(_env_file=None, **{**BASE, **over})


def test_stripe_is_the_default_provider():
    assert make().PAYMENTS_PROVIDER == "stripe"


def test_live_stripe_needs_a_stripe_secret_key_and_no_ifthenpay_credentials():
    for key in ("", "   ", "pk_test_publishable", "whsec_abc", "MBW-123"):
        with pytest.raises(ValidationError, match="STRIPE_SECRET_KEY"):
            make(PAYMENTS_MODE="live", STRIPE_SECRET_KEY=key, **WEBHOOK)

    for key in ("sk_live_" + "b" * 40, "rk_live_" + "c" * 40):
        settings_ = make(PAYMENTS_MODE="live", STRIPE_SECRET_KEY=key, **WEBHOOK)
        assert settings_.PAYMENTS_MODE == "live"


@pytest.mark.parametrize("key", [SECRET, "rk_test_" + "c" * 40])
def test_a_sandbox_key_is_refused_in_production_unless_it_is_allowed(key):
    with pytest.raises(ValidationError, match="test key"):
        make(PAYMENTS_MODE="live", STRIPE_SECRET_KEY=key, **WEBHOOK)
    allowed = make(
        PAYMENTS_MODE="live",
        STRIPE_SECRET_KEY=key,
        STRIPE_ALLOW_TEST_KEY=True,
        **WEBHOOK,
    )
    assert allowed.PAYMENTS_MODE == "live"


def test_a_sandbox_key_is_fine_outside_production_and_when_payments_are_not_live():
    live = dict(PAYMENTS_MODE="live", STRIPE_SECRET_KEY=SECRET, **WEBHOOK)
    assert make(ENVIRONMENT="dev", **live).PAYMENTS_MODE == "live"
    assert make(PAYMENTS_MODE="simulated", STRIPE_SECRET_KEY=SECRET)


def test_the_live_key_is_never_blocked_by_the_test_key_switch():
    live = dict(
        PAYMENTS_MODE="live", STRIPE_SECRET_KEY="sk_live_" + "b" * 40, **WEBHOOK
    )
    assert make(**live).PAYMENTS_MODE == "live"
    assert make(STRIPE_ALLOW_TEST_KEY=True, **live).PAYMENTS_MODE == "live"


def test_the_test_key_switch_is_off_by_default():
    assert make().STRIPE_ALLOW_TEST_KEY is False


@pytest.mark.parametrize(
    ("key", "mode"),
    [
        ("sk_test_abc", "test"),
        ("rk_test_abc", "test"),
        ("sk_live_abc", "live"),
        ("rk_live_abc", "live"),
        ("", "unknown"),
        ("pk_live_abc", "unknown"),
        ("sk_abc", "unknown"),
    ],
)
def test_the_mode_of_a_stripe_key(key, mode):
    assert stripe_key_mode(key) == mode


@pytest.mark.parametrize("secret", ["", "  ", "sk_test_abc", "pk_test_abc", "abc"])
def test_live_stripe_needs_the_webhook_signing_secret(secret):
    with pytest.raises(ValidationError, match="STRIPE_WEBHOOK_SECRET"):
        make(
            PAYMENTS_MODE="live", STRIPE_SECRET_KEY=SECRET, STRIPE_WEBHOOK_SECRET=secret
        )


def test_the_stripe_key_is_trimmed():
    assert make(STRIPE_SECRET_KEY=f"  {SECRET}\n").STRIPE_SECRET_KEY == SECRET


def test_live_ifthenpay_still_needs_its_own_credentials_and_not_a_stripe_key():
    with pytest.raises(ValidationError, match="MBWAY_KEY"):
        make(PAYMENTS_MODE="live", PAYMENTS_PROVIDER="ifthenpay")


def test_the_factory_picks_the_gateway_from_the_provider(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "live")
    monkeypatch.setattr(settings, "PAYMENTS_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", SECRET)

    gateway = get_mbway_gateway()

    assert isinstance(gateway, StripeMBWayGateway)
    assert gateway.name == "stripe"
    assert gateway.secret_key == SECRET
