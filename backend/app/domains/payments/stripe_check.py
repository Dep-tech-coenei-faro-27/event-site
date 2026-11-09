"""Check, read only, the Stripe account this server is configured with.

    python -m app.domains.payments.stripe_check

Run it after changing the keys or the webhook, and before the sales open. It answers
what a payment cannot: which account the key belongs to, whether it is a test or a
live key, whether MB WAY is active on it, and whether an enabled webhook endpoint
points at *this* site with the four events we handle. It cannot tell if
``STRIPE_WEBHOOK_SECRET`` is the secret of that endpoint (Stripe never shows it
again): the first payment does, with a ``200`` from Stripe in the log. Nothing secret
is printed, and nothing is changed at Stripe. Exit code 1 if anything is wrong.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from urllib import parse

from app.core.config import settings, stripe_key_mode
from app.domains.payments.gateway import PaymentGatewayError, StripeMBWayGateway

WEBHOOK_PATH = "/api/payment/stripe/webhook"
EXPECTED_EVENTS = {
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.canceled",
    "charge.refunded",
}


@dataclass(frozen=True)
class Line:
    ok: bool | None  # True: fine, False: wrong, None: for information
    text: str


def _host(url: object) -> str:
    return parse.urlparse(url).netloc if isinstance(url, str) else "?"


def _safe(exc: Exception, key: str) -> str:
    """The error text with the key (if Stripe repeats it) hidden."""
    return str(exc).replace(key, "<key>") if key else str(exc)


def run_checks(
    read: Callable[[str, dict | None], dict],
    *,
    key: str,
    webhook_secret: str,
    site_url: str,
    environment: str,
    allow_test_key: bool,
) -> list[Line]:
    lines: list[Line] = []
    mode = stripe_key_mode(key)
    lines.append(Line(mode != "unknown", f"key: {mode}"))
    if mode == "test":
        refused = environment == "prod" and not allow_test_key
        lines.append(
            Line(
                False if refused else None,
                "sandbox key: payments are not real and any phone number is approved"
                + (" (refused in production)" if refused else ""),
            )
        )

    try:
        account = read("/account", None)
    except PaymentGatewayError as exc:
        lines.append(Line(False, f"cannot read the account: {_safe(exc, key)}"))
        account = {}
    if account:
        name = (
            ((account.get("settings") or {}).get("dashboard") or {}).get("display_name")
            or (account.get("business_profile") or {}).get("name")
            or "(no name)"
        )
        lines.append(
            Line(
                None,
                f"account: {account.get('id')} · {name} · {account.get('country')}",
            )
        )
        capability = (account.get("capabilities") or {}).get("mb_way_payments")
        lines.append(
            Line(
                capability == "active",
                f"MB WAY on the account: {capability or 'absent'}",
            )
        )
        if mode == "live":
            lines.append(
                Line(bool(account.get("charges_enabled")), "can charge (live)")
            )
            lines.append(
                Line(bool(account.get("payouts_enabled")), "can pay out (live)")
            )

    lines.append(
        Line(
            webhook_secret.startswith("whsec_"),
            "STRIPE_WEBHOOK_SECRET looks like a signing secret",
        )
    )
    expected_url = f"{site_url.rstrip('/')}{WEBHOOK_PATH}"
    try:
        endpoints = read("/webhook_endpoints", {"limit": 100}).get("data") or []
    except PaymentGatewayError as exc:
        lines.append(
            Line(False, f"cannot read the webhook endpoints: {_safe(exc, key)}")
        )
        return lines
    ours = [
        e for e in endpoints if isinstance(e, dict) and e.get("url") == expected_url
    ]
    if not ours:
        others = sorted({_host(e.get("url")) for e in endpoints if isinstance(e, dict)})
        lines.append(
            Line(
                False,
                f"no webhook endpoint for {expected_url} in this account; "
                f"the account has {len(endpoints)}, pointing at: "
                f"{', '.join(others) or 'none'}",
            )
        )
        return lines
    endpoint = ours[0]
    lines.append(
        Line(
            endpoint.get("status") == "enabled",
            f"webhook endpoint {expected_url}: {endpoint.get('status')}",
        )
    )
    events = set(endpoint.get("enabled_events") or [])
    missing = sorted(EXPECTED_EVENTS - events) if "*" not in events else []
    lines.append(
        Line(
            not missing,
            "webhook events: "
            + ("all four handled" if not missing else "missing " + ", ".join(missing)),
        )
    )
    if mode != "unknown":
        same = bool(endpoint.get("livemode")) == (mode == "live")
        lines.append(
            Line(
                same,
                "the endpoint is in "
                f"{'live' if endpoint.get('livemode') else 'test'} mode, "
                f"{'like' if same else 'unlike'} the key",
            )
        )
    return lines


def main() -> None:
    gateway = StripeMBWayGateway(
        secret_key=settings.STRIPE_SECRET_KEY,
        timeout_seconds=settings.MBWAY_TIMEOUT_SECONDS,
        api_version=settings.STRIPE_API_VERSION,
    )
    lines = run_checks(
        gateway.read,
        key=settings.STRIPE_SECRET_KEY,
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
        site_url=settings.FRONTEND_URL,
        environment=settings.ENVIRONMENT,
        allow_test_key=settings.STRIPE_ALLOW_TEST_KEY,
    )
    for line in lines:
        mark = "  " if line.ok is None else ("OK" if line.ok else "!!")
        print(f"{mark} {line.text}")
    failed = [line for line in lines if line.ok is False]
    print(f"\n{len(failed)} problem(s)." if failed else "\nAll good.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
