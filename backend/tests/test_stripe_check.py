import pytest

from app.core.config import settings
from app.domains.payments.gateway import PaymentGatewayError, StripeMBWayGateway
from app.domains.payments.stripe_check import EXPECTED_EVENTS, Line, run_checks
from app.main import create_app

SITE = "https://ualg.eneiconf.pt"
URL = f"{SITE}/api/payment/stripe/webhook"
WHSEC = "whsec_" + "w" * 32

ACCOUNT = {
    "id": "acct_123",
    "country": "PT",
    "charges_enabled": True,
    "payouts_enabled": True,
    "settings": {"dashboard": {"display_name": "ENEI"}},
    "capabilities": {"mb_way_payments": "active"},
}


def endpoint(url=URL, status="enabled", events=None, livemode=False):
    return {
        "url": url,
        "status": status,
        "enabled_events": sorted(EXPECTED_EVENTS if events is None else events),
        "livemode": livemode,
    }


def reader(account=ACCOUNT, endpoints=None, fail=()):
    answers = {
        "/account": account,
        "/webhook_endpoints": {
            "data": [endpoint()] if endpoints is None else endpoints
        },
    }

    def read(path, params):
        if path in fail:
            raise PaymentGatewayError("stripe responded with HTTP 403 (no access)")
        return answers[path]

    return read


def check(read=None, **over):
    args = dict(
        key="sk_test_" + "a" * 20,
        webhook_secret=WHSEC,
        site_url=SITE,
        environment="dev",
        allow_test_key=False,
    )
    return run_checks(read or reader(), **{**args, **over})


def wrong(lines):
    return [line.text for line in lines if line.ok is False]


def test_a_well_set_up_test_account_has_nothing_wrong():
    lines = check()
    assert wrong(lines) == []
    assert any("acct_123" in line.text and "ENEI" in line.text for line in lines)


def test_a_live_key_checks_that_the_account_can_charge_and_pay_out():
    live = check(reader(endpoints=[endpoint(livemode=True)]), key="sk_live_" + "a" * 20)
    assert wrong(live) == []
    no_charges = {**ACCOUNT, "charges_enabled": False, "payouts_enabled": False}
    bad = check(
        reader(account=no_charges, endpoints=[endpoint(livemode=True)]),
        key="sk_live_" + "a" * 20,
    )
    assert wrong(bad) == ["can charge (live)", "can pay out (live)"]


def test_a_test_key_is_flagged_as_wrong_in_production_unless_allowed():
    assert any("refused" in t for t in wrong(check(environment="prod")))
    assert wrong(check(environment="prod", allow_test_key=True)) == []


def test_a_key_that_is_not_a_stripe_secret_key_is_wrong():
    assert "key: unknown" in wrong(check(key="pk_live_abc"))


def test_mb_way_not_active_on_the_account_is_wrong():
    for capabilities in (
        {},
        {"mb_way_payments": "inactive"},
        {"mb_way_payments": "pending"},
    ):
        account = {**ACCOUNT, "capabilities": capabilities}
        assert any("MB WAY" in t for t in wrong(check(reader(account=account))))


def test_no_endpoint_for_this_site_names_where_the_others_point():
    others = [endpoint(url="https://neei.online/webhook")]
    problems = wrong(check(reader(endpoints=others)))
    assert len(problems) == 1
    assert "neei.online" in problems[0] and URL in problems[0]
    assert "/webhook" not in problems[0].replace("/api/payment/stripe/webhook", "")


def test_an_endpoint_of_another_path_is_not_ours():
    other = [endpoint(url=f"{SITE}/api/payment/callback")]
    assert any(
        "no webhook endpoint" in t for t in wrong(check(reader(endpoints=other)))
    )


def test_a_trailing_slash_in_the_site_address_does_not_matter():
    assert wrong(check(site_url=SITE + "/")) == []


def test_a_disabled_endpoint_is_wrong():
    disabled = [endpoint(status="disabled")]
    assert wrong(check(reader(endpoints=disabled))) == [
        f"webhook endpoint {URL}: disabled"
    ]


def test_an_endpoint_missing_an_event_says_which():
    partial = [endpoint(events=["payment_intent.succeeded"])]
    problems = wrong(check(reader(endpoints=partial)))
    assert problems == [
        "webhook events: missing payment_intent.canceled, payment_intent.payment_failed"
    ]


def test_an_endpoint_listening_to_everything_is_enough():
    assert wrong(check(reader(endpoints=[endpoint(events=["*"])]))) == []


def test_an_endpoint_in_the_other_mode_is_wrong():
    live_endpoint = [endpoint(livemode=True)]
    assert any(
        "like the key" in t for t in wrong(check(reader(endpoints=live_endpoint)))
    )


@pytest.mark.parametrize("secret", ["", "sk_test_abc", "abc"])
def test_a_webhook_secret_that_is_not_a_signing_secret_is_wrong(secret):
    assert wrong(check(webhook_secret=secret)) == [
        "STRIPE_WEBHOOK_SECRET looks like a signing secret"
    ]


@pytest.mark.parametrize("path", ["/account", "/webhook_endpoints"])
def test_a_refused_read_is_reported_and_the_rest_still_runs(path):
    lines = check(reader(fail=(path,)))
    assert any(t.startswith("cannot read") for t in wrong(lines))
    assert any(line.text.startswith("key:") for line in lines)


def test_nothing_secret_is_ever_printed():
    key = "sk_test_" + "SECRETKEYVALUE" * 3
    text = "\n".join(line.text for line in check(key=key, webhook_secret=WHSEC))
    assert key not in text and WHSEC not in text


def test_only_reads_are_made():
    seen = []

    def read(path, params):
        seen.append(path)
        return reader()(path, params)

    check(read)
    assert seen == ["/account", "/webhook_endpoints"]


def test_line_is_a_plain_value():
    assert Line(True, "x") == Line(True, "x")


def test_read_is_a_get_with_the_query_and_no_body():
    calls = []

    def fake(method, url, form, headers):
        calls.append((method, url, form))
        return {"data": []}

    gateway = StripeMBWayGateway(
        secret_key="sk_test_x",
        timeout_seconds=5,
        api_version="v",
        http_request=fake,
    )
    gateway.read("/webhook_endpoints", {"limit": 100})
    gateway.read("/account")
    assert calls == [
        ("GET", "https://api.stripe.com/v1/webhook_endpoints?limit=100", None),
        ("GET", "https://api.stripe.com/v1/account", None),
    ]


@pytest.mark.parametrize(
    ("key", "environment", "allow", "expected"),
    [
        # a exceção do staging: chave de teste em produção, com a Variable ligada
        (
            "sk_test_" + "a" * 20,
            "prod",
            True,
            ["test key", "STRIPE_ALLOW_TEST_KEY is on"],
        ),
        # o arranque recusa isto (a guarda da configuração); se o log fosse
        # chamado assim, não podia dizer que a Variable está ligada
        ("sk_test_" + "a" * 20, "prod", False, ["test key"]),
        ("sk_test_" + "a" * 20, "dev", True, ["test key"]),
        ("sk_test_" + "a" * 20, "dev", False, ["test key"]),
        ("sk_live_" + "a" * 20, "prod", False, ["live key"]),
        ("sk_live_" + "a" * 20, "prod", True, ["live key"]),
    ],
)
def test_the_startup_log_says_which_kind_of_key_is_in_use(
    monkeypatch, caplog, key, environment, allow, expected
):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "live")
    monkeypatch.setattr(settings, "PAYMENTS_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", key)
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(settings, "STRIPE_ALLOW_TEST_KEY", allow)
    with caplog.at_level("INFO"):
        create_app()
    text = " | ".join(record.getMessage() for record in caplog.records)
    for part in expected:
        assert part in text
    assert key not in text
    assert ("STRIPE_ALLOW_TEST_KEY is on" in text) == (
        "STRIPE_ALLOW_TEST_KEY is on" in expected
    )


def test_an_endpoint_of_another_site_with_the_same_path_is_not_ours():
    """The NEEI endpoint ends in the same path: only the whole address counts."""
    other = endpoint(url="https://neei.online/api/payment/stripe/webhook")

    found = wrong(check(reader(endpoints=[other])))

    assert found and "no webhook endpoint for" in found[0]
    assert "neei.online" in found[0]


def test_a_mode_mismatch_says_unlike_not_like():
    found = wrong(check(reader(endpoints=[endpoint(livemode=True)])))

    assert found == ["the endpoint is in live mode, unlike the key"]


def test_a_stripe_error_that_repeats_the_key_is_hidden():
    key = "sk_test_" + "SECRETVALUE" * 3

    def read(path, params):
        raise PaymentGatewayError(
            f"stripe responded with HTTP 401: Invalid API Key provided: {key}"
        )

    lines = check(read, key=key)

    text = " | ".join(line.text for line in lines)
    assert "SECRETVALUE" not in text
    assert "<key>" in text


@pytest.mark.parametrize(("good", "code"), [(True, 0), (False, 1)])
def test_the_command_exits_with_1_when_something_is_wrong(
    monkeypatch, capsys, good, code
):
    from app.domains.payments import stripe_check

    class FakeGateway:
        def __init__(self, **kwargs):
            pass

        read = staticmethod(reader(endpoints=None if good else []))

    monkeypatch.setattr(stripe_check, "StripeMBWayGateway", FakeGateway)
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_" + "a" * 20)
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", WHSEC)
    monkeypatch.setattr(settings, "FRONTEND_URL", SITE)
    monkeypatch.setattr(settings, "ENVIRONMENT", "dev")

    with pytest.raises(SystemExit) as exit_info:
        stripe_check.main()

    assert exit_info.value.code == code
    assert ("All good." in capsys.readouterr().out) == good
