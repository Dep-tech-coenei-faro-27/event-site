"""Stripe webhook signature check (docs.stripe.com/webhooks#verify-manually).

The header looks like ``t=1492774577,v1=<hex>,v1=<hex>,v0=<hex>``: ``t`` is when
Stripe signed the event and each ``v1`` is the HMAC-SHA256, keyed with the endpoint
secret, of ``"<t>.<raw body>"``. More than one ``v1`` appears while a secret is
being rolled. The body must be checked exactly as it arrived, never re-serialised.
"""

import hashlib
import hmac
import time


class InvalidStripeSignatureError(ValueError):
    """The event does not come from Stripe, or is too old (or new) to trust."""


def verify_signature(
    payload: bytes,
    header: str | None,
    secret: str,
    *,
    tolerance_seconds: int,
    now: float | None = None,
) -> None:
    if not secret:
        raise InvalidStripeSignatureError("webhook secret is not configured")
    if not header:
        raise InvalidStripeSignatureError("missing Stripe-Signature header")

    timestamp: int | None = None
    signatures: list[str] = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        raise InvalidStripeSignatureError("malformed Stripe-Signature header")

    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise InvalidStripeSignatureError("signature does not match")

    # Checked after the signature so a forged timestamp tells nothing. The window
    # applies in both directions: an event "from the future" is not trusted either.
    if abs((time.time() if now is None else now) - timestamp) > tolerance_seconds:
        raise InvalidStripeSignatureError("timestamp outside the tolerance")
