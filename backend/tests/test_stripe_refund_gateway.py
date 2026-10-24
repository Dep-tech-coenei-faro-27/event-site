"""The Stripe gateway giving money back and ending a payment that still waits."""

import io
import json
from urllib import error, parse

import pytest

from app.domains.payments import gateway as gateway_module
from app.domains.payments.gateway import (
    AlreadyRefundedError,
    CancellingGateway,
    IfThenPayMBWayGateway,
    LookupGateway,
    PaymentGatewayError,
    RefundingGateway,
    SimulatedMBWayGateway,
    StripeMBWayGateway,
)
from app.domains.payments.models import TransactionStatus

SECRET = "sk_test_" + "a" * 40
INTENT = "pi_3USkViKnHPoxsDHG1o4JvnxP"
REFERENCE = "ENEI-0000000001"
AMOUNT = 2500
BASE = "https://api.stripe.com/v1"


def paid(**extra):
    return {
        "id": INTENT,
        "status": "succeeded",
        "currency": "eur",
        "amount_received": AMOUNT,
        "metadata": {"reference": REFERENCE},
        **extra,
    }


def waiting(status="requires_action", **extra):
    return {
        "id": INTENT,
        "status": status,
        "metadata": {"reference": REFERENCE},
        **extra,
    }


def stripe_error(code, status=400):
    return PaymentGatewayError(
        f"stripe responded with HTTP {status} ({code})", code=code
    )


def build(routes):
    """A gateway whose Stripe answers come from ``routes``: ``{(method, url): answer}``.

    An answer may be a dict, an exception (raised), or a list of them (one per call).
    """
    calls: list[tuple] = []

    def fake_request(method, url, form, headers):
        calls.append((method, url, form, headers))
        answer = routes[(method, url)]
        if isinstance(answer, list):
            answer = answer.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    gateway = StripeMBWayGateway(
        secret_key=SECRET,
        timeout_seconds=10,
        api_version="2026-08-26.dahlia",
        http_request=fake_request,
    )
    return gateway, calls


GET_INTENT = ("GET", f"{BASE}/payment_intents/{INTENT}")
POST_REFUND = ("POST", f"{BASE}/refunds")
POST_CANCEL = ("POST", f"{BASE}/payment_intents/{INTENT}/cancel")


def refund(gateway, *, amount=AMOUNT, reference=REFERENCE, provider_reference=INTENT):
    return gateway.refund(
        reference=reference,
        provider_reference=provider_reference,
        amount_cents=amount,
    )


def cancel(gateway, *, reference=REFERENCE, provider_reference=INTENT):
    return gateway.cancel_payment(
        reference=reference, provider_reference=provider_reference
    )


def posts(calls):
    return [call for call in calls if call[0] == "POST"]


# --- refund --------------------------------------------------------------------------


def test_a_refund_gives_back_the_whole_payment_with_an_idempotency_key():
    gateway, calls = build(
        {GET_INTENT: paid(), POST_REFUND: {"id": "re_3USkVi", "status": "succeeded"}}
    )

    assert refund(gateway) == "re_3USkVi"

    (method, url, form, headers) = posts(calls)[0]
    assert (method, url) == POST_REFUND
    assert form == {
        "payment_intent": INTENT,
        "amount": str(AMOUNT),
        "reason": "requested_by_customer",
        "metadata[reference]": REFERENCE,
    }
    # The same payment is always the same refund: a repeat never refunds twice.
    assert headers["Idempotency-Key"] == f"enei-refund-{REFERENCE}"
    assert headers["Stripe-Version"] == "2026-08-26.dahlia"


def test_a_refund_that_stripe_is_still_processing_counts_as_accepted():
    gateway, _ = build(
        {GET_INTENT: paid(), POST_REFUND: {"id": "re_1", "status": "pending"}}
    )

    assert refund(gateway) == "re_1"


@pytest.mark.parametrize("refund_id", ["re_3USkVi", "pyr_1UTtBwKnHPoxsDHGHc9dIga1"])
def test_the_refund_id_of_a_card_and_of_an_mb_way_payment_are_both_accepted(refund_id):
    """The sandbox answers an MB WAY refund with a ``pyr_`` id, still ``pending``."""
    gateway, _ = build(
        {GET_INTENT: paid(), POST_REFUND: {"id": refund_id, "status": "pending"}}
    )

    assert refund(gateway) == refund_id


@pytest.mark.parametrize("status", ["failed", "canceled", "requires_action", None])
def test_a_refund_stripe_did_not_accept_is_an_error(status):
    gateway, _ = build(
        {GET_INTENT: paid(), POST_REFUND: {"id": "re_1", "status": status}}
    )

    with pytest.raises(PaymentGatewayError, match="not accepted"):
        refund(gateway)


@pytest.mark.parametrize(
    "body", [{}, {"status": "succeeded"}, {"id": "xx_1", "status": "succeeded"}]
)
def test_an_answer_without_a_refund_id_is_an_error(body):
    gateway, _ = build({GET_INTENT: paid(), POST_REFUND: body})

    with pytest.raises(PaymentGatewayError, match="refund id"):
        refund(gateway)


def test_a_payment_already_refunded_in_full_is_told_apart_from_other_errors():
    gateway, _ = build(
        {GET_INTENT: paid(), POST_REFUND: stripe_error("charge_already_refunded")}
    )

    with pytest.raises(AlreadyRefundedError):
        refund(gateway)


def test_any_other_error_of_stripe_stays_a_plain_gateway_error():
    gateway, _ = build(
        {GET_INTENT: paid(), POST_REFUND: stripe_error("api_error", 500)}
    )

    with pytest.raises(PaymentGatewayError) as raised:
        refund(gateway)
    assert not isinstance(raised.value, AlreadyRefundedError)


@pytest.mark.parametrize(
    ("intent", "why"),
    [
        (paid(metadata={"reference": "ENEI-9999999999"}), "does not belong"),
        (paid(metadata={}), "does not belong"),
        (waiting(), "not paid"),
        (waiting("canceled"), "not paid"),
        (paid(amount_received=AMOUNT - 1), "another amount"),
        (paid(amount_received=AMOUNT + 1), "another amount"),
        (paid(currency="usd"), "another amount"),
    ],
)
def test_nothing_is_refunded_unless_it_is_this_payment_paid_for_what_we_charged(
    intent, why
):
    gateway, calls = build(
        {GET_INTENT: intent, POST_REFUND: {"id": "re_1", "status": "succeeded"}}
    )

    with pytest.raises(PaymentGatewayError, match=why):
        refund(gateway)

    assert posts(calls) == []  # not a single refund request was sent


@pytest.mark.parametrize("provider_reference", [None, "", "not-an-intent", "pi_x/../y"])
def test_a_refund_needs_a_real_payment_intent_id(provider_reference):
    gateway, calls = build({})

    with pytest.raises(PaymentGatewayError, match="not a Stripe PaymentIntent id"):
        refund(gateway, provider_reference=provider_reference)

    assert calls == []


# --- ending a payment that still waits ----------------------------------------


def test_a_payment_that_still_waits_is_cancelled():
    gateway, calls = build({GET_INTENT: waiting(), POST_CANCEL: waiting("canceled")})

    assert cancel(gateway) is TransactionStatus.EXPIRED

    (method, url, form, headers) = posts(calls)[0]
    assert (method, url) == POST_CANCEL
    assert form == {"cancellation_reason": "abandoned"}
    assert headers["Idempotency-Key"] == f"enei-cancel-{REFERENCE}"


def test_a_payment_that_was_already_paid_is_never_cancelled_and_counts_as_paid():
    gateway, calls = build({GET_INTENT: paid()})

    assert cancel(gateway) is TransactionStatus.CONFIRMED
    assert posts(calls) == []


def test_a_payment_that_stripe_already_cancelled_needs_no_request():
    gateway, calls = build({GET_INTENT: waiting("canceled")})

    assert cancel(gateway) is TransactionStatus.EXPIRED
    assert posts(calls) == []


def test_approved_at_the_very_moment_it_is_paid_and_not_expired():
    """Stripe says it is waiting, the person approves, and the cancel is refused."""
    gateway, calls = build(
        {
            GET_INTENT: [waiting(), paid()],
            POST_CANCEL: stripe_error("payment_intent_unexpected_state"),
        }
    )

    assert cancel(gateway) is TransactionStatus.CONFIRMED
    assert len(posts(calls)) == 1


def test_a_refusal_with_only_a_message_and_no_code_is_read_the_same_way():
    """The sandbox sometimes answers "already in a terminal state" with no code."""
    gateway, _ = build(
        {
            GET_INTENT: [waiting(), paid()],
            POST_CANCEL: PaymentGatewayError("already in a terminal state"),
        }
    )

    assert cancel(gateway) is TransactionStatus.CONFIRMED


def test_a_refusal_while_the_intent_still_reads_as_waiting_leaves_the_payment_alone():
    """Approval in flight: Stripe refuses and still says it waits; nothing decided."""
    gateway, _ = build(
        {
            GET_INTENT: [waiting(), waiting()],
            POST_CANCEL: PaymentGatewayError("already in a terminal state"),
        }
    )

    with pytest.raises(PaymentGatewayError, match="terminal state"):
        cancel(gateway)


def test_when_the_intent_cannot_be_read_again_the_original_refusal_is_raised():
    gateway, _ = build(
        {
            GET_INTENT: [waiting(), PaymentGatewayError("stripe unreachable")],
            POST_CANCEL: PaymentGatewayError("already in a terminal state"),
        }
    )

    with pytest.raises(PaymentGatewayError, match="terminal state"):
        cancel(gateway)


def test_cancelled_by_stripe_at_the_very_moment_is_expired():
    gateway, _ = build(
        {
            GET_INTENT: [waiting(), waiting("canceled")],
            POST_CANCEL: stripe_error("payment_intent_unexpected_state"),
        }
    )

    assert cancel(gateway) is TransactionStatus.EXPIRED


def test_a_state_that_cannot_be_cancelled_and_is_not_over_stays_an_error():
    """Still processing: Stripe refuses and the payment is neither paid nor over."""
    gateway, _ = build(
        {
            GET_INTENT: [waiting("processing"), waiting("processing")],
            POST_CANCEL: stripe_error("payment_intent_unexpected_state"),
        }
    )

    with pytest.raises(PaymentGatewayError):
        cancel(gateway)


def test_any_other_error_when_cancelling_is_raised():
    gateway, _ = build(
        {GET_INTENT: waiting(), POST_CANCEL: stripe_error("api_error", 500)}
    )

    with pytest.raises(PaymentGatewayError):
        cancel(gateway)


def test_a_payment_intent_of_another_payment_is_never_cancelled():
    gateway, calls = build(
        {GET_INTENT: waiting(metadata={"reference": "ENEI-9999999999"})}
    )

    with pytest.raises(PaymentGatewayError, match="does not belong"):
        cancel(gateway)

    assert posts(calls) == []


# --- finding a payment whose id we never saved -------------------------------------


def search_url(reference=REFERENCE):
    query = parse.urlencode({"query": f"metadata['reference']:'{reference}'"})
    return ("GET", f"{BASE}/payment_intents/search?{query}")


def find(gateway, reference=REFERENCE):
    return gateway.find_payment(reference=reference)


def test_a_payment_whose_id_was_lost_is_found_by_its_reference():
    gateway, calls = build({search_url(): {"data": [waiting()]}})

    assert find(gateway) == INTENT
    assert calls[0][0] == "GET"


def test_not_found_yet_is_not_an_answer():
    gateway, _ = build({search_url(): {"data": []}})

    assert find(gateway) is None


def test_more_than_one_match_is_not_an_answer():
    other = {**waiting(), "id": "pi_3OtherIntentIdxxxxxxxx"}
    gateway, _ = build({search_url(): {"data": [waiting(), other]}})

    assert find(gateway) is None


def test_a_match_of_another_reference_is_ignored():
    stray = waiting(metadata={"reference": "ENEI-9999999999"})
    gateway, _ = build({search_url(): {"data": [stray]}})

    assert find(gateway) is None


@pytest.mark.parametrize(
    "bad", ["", "ENEI-1", "x' OR 1=1", "ENEI-00000000011", "enei-0000000001"]
)
def test_only_a_well_formed_reference_is_ever_sent_in_a_search(bad):
    gateway, calls = build({})

    with pytest.raises(PaymentGatewayError, match="not a payment reference"):
        find(gateway, bad)

    assert calls == []


def test_a_failed_search_is_an_error_and_not_an_answer():
    gateway, _ = build({search_url(): stripe_error("api_error", 500)})

    with pytest.raises(PaymentGatewayError):
        find(gateway)


# --- the error code travels with the error ------------------------------------


def http_error(code, body):
    return error.HTTPError("https://api.stripe.com", code, "x", {}, io.BytesIO(body))


def test_the_code_of_a_stripe_error_is_kept_on_the_exception(monkeypatch):
    body = json.dumps(
        {"error": {"type": "invalid_request_error", "code": "charge_already_refunded"}}
    ).encode()

    def refuse(req, timeout):
        raise http_error(400, body)

    monkeypatch.setattr(gateway_module.request, "urlopen", refuse)
    gateway = StripeMBWayGateway(
        secret_key=SECRET, timeout_seconds=10, api_version="2026-08-26.dahlia"
    )

    with pytest.raises(PaymentGatewayError) as raised:
        gateway._request_json("POST", f"{BASE}/refunds", {}, {})

    assert raised.value.code == "charge_already_refunded"
    assert SECRET not in str(raised.value)


def test_an_error_without_a_code_has_no_code(monkeypatch):
    def refuse(req, timeout):
        raise http_error(502, b"<html>bad gateway</html>")

    monkeypatch.setattr(gateway_module.request, "urlopen", refuse)
    gateway = StripeMBWayGateway(
        secret_key=SECRET, timeout_seconds=10, api_version="2026-08-26.dahlia"
    )

    with pytest.raises(PaymentGatewayError) as raised:
        gateway._request_json("GET", f"{BASE}/payment_intents/x", None, {})

    assert raised.value.code is None


# --- who can do what ----------------------------------------------------------


def test_only_stripe_cancels_and_only_stripe_and_the_simulator_refund():
    stripe = StripeMBWayGateway(
        secret_key=SECRET, timeout_seconds=10, api_version="2026-08-26.dahlia"
    )
    ifthenpay = IfThenPayMBWayGateway(
        mbway_key="k", base_url="https://x", timeout_seconds=10
    )
    simulated = SimulatedMBWayGateway()

    assert isinstance(stripe, RefundingGateway) and isinstance(
        stripe, CancellingGateway
    )
    assert isinstance(stripe, LookupGateway)
    assert not isinstance(ifthenpay, LookupGateway)
    assert isinstance(simulated, RefundingGateway)
    assert not isinstance(simulated, CancellingGateway)
    # ifthenpay has no refund API: that is done by hand in its panel.
    assert not isinstance(ifthenpay, RefundingGateway)
    assert not isinstance(ifthenpay, CancellingGateway)


def test_the_simulated_refund_moves_nothing_and_says_so():
    assert (
        SimulatedMBWayGateway().refund(
            reference=REFERENCE, provider_reference="SIM-1-x", amount_cents=AMOUNT
        )
        == f"SIMREFUND-{REFERENCE}"
    )
