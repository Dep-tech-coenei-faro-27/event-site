import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.domains.payments.gateway import MBWayPayment, get_mbway_gateway
from app.domains.payments.models import TicketTier, Transaction, TransactionStatus
from app.domains.payments.stripe_webhook import (
    InvalidStripeSignatureError,
    verify_signature,
)
from app.domains.tickets.models import PaymentStatus, Ticket
from app.main import app
from tests.helpers import INITIATE_URL, authenticate, seed_ticket_tiers

WEBHOOK_URL = "/api/payment/stripe/webhook"
SECRET = "whsec_" + "a" * 32
INTENT = "pi_3USkViKnHPoxsDHG1o4JvnxP"
AMOUNT = 5000  # TicketTier.GERAL in the test prices

INITIATE = {"ticket_tier": TicketTier.GERAL.value, "phone": "912345678"}


def sign(payload: bytes, *, secret=SECRET, timestamp=None) -> str:
    t = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256)
    return f"t={t},v1={digest.hexdigest()}"


# --- the signature check -------------------------------------------------------


def check(payload=b'{"id":"evt_1"}', header=None, secret=SECRET, now=None, **kw):
    verify_signature(
        payload,
        sign(payload, timestamp=1_700_000_000) if header is None else header,
        secret,
        tolerance_seconds=kw.get("tolerance_seconds", 300),
        now=1_700_000_000 if now is None else now,
    )


def test_a_good_signature_passes():
    check()


def test_a_signature_at_the_edge_of_the_tolerance_passes():
    check(now=1_700_000_300)
    check(now=1_699_999_700)


@pytest.mark.parametrize("now", [1_700_000_301, 1_699_999_699])
def test_a_timestamp_outside_the_tolerance_is_refused_in_both_directions(now):
    with pytest.raises(InvalidStripeSignatureError, match="tolerance"):
        check(now=now)


def test_a_signature_made_with_another_secret_is_refused():
    header = sign(b'{"id":"evt_1"}', secret="whsec_other", timestamp=1_700_000_000)
    with pytest.raises(InvalidStripeSignatureError, match="does not match"):
        check(header=header)


def test_a_tampered_body_is_refused():
    header = sign(b'{"id":"evt_1"}', timestamp=1_700_000_000)
    with pytest.raises(InvalidStripeSignatureError, match="does not match"):
        check(payload=b'{"id":"evt_2"}', header=header)


def test_a_signature_over_another_timestamp_is_refused():
    good = sign(b'{"id":"evt_1"}', timestamp=1_700_000_000)
    forged = good.replace("t=1700000000", "t=1700000100")
    with pytest.raises(InvalidStripeSignatureError):
        check(header=forged, now=1_700_000_100)


def test_any_of_several_v1_signatures_is_enough():
    good = sign(b'{"id":"evt_1"}', timestamp=1_700_000_000)
    check(header=f"{good},v1={'0' * 64},v0=abc")
    check(header=f"t=1700000000,v1={'0' * 64},{good.split(',', 1)[1]}")


@pytest.mark.parametrize(
    "header", [None, "", "garbage", "t=abc,v1=" + "0" * 64, "t=1700000000", "v1=ab"]
)
def test_a_missing_or_malformed_header_is_refused(header):
    with pytest.raises(InvalidStripeSignatureError):
        verify_signature(
            b"{}", header, SECRET, tolerance_seconds=300, now=1_700_000_000
        )


# Characters that ``str.isdigit`` accepts but ``int`` does not, a non-ASCII signature
# (``hmac.compare_digest`` refuses it) and a timestamp past the limit of ``int``.
ODD_HEADERS = [
    "t=\u00b2,v1=" + "0" * 64,
    "t=1700000000,v1=\u00e9" + "0" * 63,
    "t=" + "9" * 5000 + ",v1=" + "0" * 64,
]


@pytest.mark.parametrize("header", ODD_HEADERS)
def test_an_odd_header_is_refused_and_never_crashes(header):
    with pytest.raises(InvalidStripeSignatureError):
        verify_signature(
            b"{}", header, SECRET, tolerance_seconds=300, now=1_700_000_000
        )


def test_without_a_configured_secret_nothing_passes():
    header = sign(b"{}", secret="", timestamp=1_700_000_000)
    with pytest.raises(InvalidStripeSignatureError, match="not configured"):
        check(payload=b"{}", header=header, secret="")


# --- the endpoint ----------------------------------------------------------------


class FakeStripeGateway:
    name = "stripe"

    def __init__(self):
        self.provider_reference = INTENT

    def create_payment(
        self, *, reference, amount_cents, phone, email, description
    ) -> MBWayPayment:
        return MBWayPayment(provider_reference=self.provider_reference)

    def get_status(self, *, reference, provider_reference) -> TransactionStatus:
        return TransactionStatus.PENDING


@pytest.fixture
def gateway():
    fake = FakeStripeGateway()
    app.dependency_overrides[get_mbway_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_mbway_gateway, None)


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SECRET)


def start_payment(auth_client, email_sender, db_session) -> str:
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    response = auth_client.post(INITIATE_URL, json=INITIATE)
    assert response.status_code == 201
    return response.json()["reference"]


def event(kind, reference, *, intent_id=INTENT, **intent):
    data = {
        "id": intent_id,
        "object": "payment_intent",
        "currency": "eur",
        "amount": AMOUNT,
        "amount_received": AMOUNT if kind == "payment_intent.succeeded" else 0,
        "metadata": {"reference": reference},
        **intent,
    }
    return {"id": "evt_1", "type": kind, "data": {"object": data}}


def post(auth_client, body, *, header=None):
    payload = body if isinstance(body, bytes) else json.dumps(body).encode()
    return auth_client.post(
        WEBHOOK_URL,
        content=payload,
        headers={
            # Bytes: a header with non-ASCII text is sent as it would arrive.
            "Stripe-Signature": (sign(payload) if header is None else header).encode(
                "latin-1"
            ),
            "Content-Type": "application/json",
        },
    )


def load(db_session, reference) -> Transaction:
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    db_session.refresh(transaction)
    return transaction


def tickets(db_session, reference) -> int:
    return db_session.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.transaction_reference == reference)
    )


def test_a_succeeded_event_confirms_the_payment_and_issues_the_ticket(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    response = post(auth_client, event("payment_intent.succeeded", reference))

    assert response.status_code == 200
    transaction = load(db_session, reference)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert transaction.confirmed_at is not None
    assert tickets(db_session, reference) == 1


def test_a_repeated_event_changes_nothing(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    body = event("payment_intent.succeeded", reference)

    assert post(auth_client, body).status_code == 200
    assert post(auth_client, body).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert tickets(db_session, reference) == 1


@pytest.mark.parametrize("local", [TransactionStatus.EXPIRED, TransactionStatus.FAILED])
def test_a_payment_we_had_given_up_on_is_still_confirmed_when_it_was_paid(
    auth_client, email_sender, db_session, gateway, local
):
    reference = start_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.status = local
    db_session.commit()

    response = post(auth_client, event("payment_intent.succeeded", reference))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert tickets(db_session, reference) == 1


@pytest.mark.parametrize(
    "wrong",
    [
        {"amount_received": AMOUNT - 1},
        {"amount_received": AMOUNT + 1},
        {"amount_received": None},
        {"currency": "usd"},
    ],
)
def test_a_payment_for_another_amount_or_currency_is_not_confirmed(
    auth_client, email_sender, db_session, gateway, wrong, caplog
):
    reference = start_payment(auth_client, email_sender, db_session)

    response = post(auth_client, event("payment_intent.succeeded", reference, **wrong))

    assert response.status_code == 200  # repeating it would not help
    assert load(db_session, reference).status is TransactionStatus.PENDING
    assert tickets(db_session, reference) == 0
    assert "needs a look" in caplog.text


def test_an_event_about_a_payment_we_do_not_know_is_acknowledged_and_ignored(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    response = post(auth_client, event("payment_intent.succeeded", "ENEI-UNKNOWN"))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.PENDING


def test_the_event_of_another_payment_intent_is_ignored(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    body = event("payment_intent.succeeded", reference, intent_id="pi_someoneelse")
    response = post(auth_client, body)

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.PENDING
    assert tickets(db_session, reference) == 0


def test_a_payment_made_through_another_provider_is_never_settled_by_stripe(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.provider = "ifthenpay"
    db_session.commit()

    response = post(auth_client, event("payment_intent.succeeded", reference))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.PENDING


def test_an_event_that_beats_the_saving_of_the_payment_intent_id_is_accepted(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.provider_reference = None  # Stripe answered before we saved it
    db_session.commit()

    response = post(auth_client, event("payment_intent.succeeded", reference))

    assert response.status_code == 200
    transaction = load(db_session, reference)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert transaction.provider_reference == INTENT


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("payment_intent_payment_attempt_expired", TransactionStatus.EXPIRED),
        ("payment_method_customer_decline", TransactionStatus.FAILED),
        ("payment_method_provider_decline", TransactionStatus.FAILED),
    ],
)
def test_a_failed_event_ends_a_waiting_payment(
    auth_client, email_sender, db_session, gateway, code, expected
):
    reference = start_payment(auth_client, email_sender, db_session)
    body = event(
        "payment_intent.payment_failed",
        reference,
        status="requires_payment_method",
        last_payment_error={"code": code},
    )

    assert post(auth_client, body).status_code == 200

    assert load(db_session, reference).status is expected


def test_a_canceled_event_ends_a_waiting_payment(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    body = event("payment_intent.canceled", reference, status="canceled")
    assert post(auth_client, body).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.FAILED


def test_a_late_failed_event_never_overwrites_a_confirmed_payment(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    assert (
        post(auth_client, event("payment_intent.succeeded", reference)).status_code
        == 200
    )

    body = event(
        "payment_intent.payment_failed",
        reference,
        status="requires_payment_method",
        last_payment_error={"code": "payment_method_customer_decline"},
    )
    assert post(auth_client, body).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert tickets(db_session, reference) == 1


def test_a_failed_event_we_cannot_read_leaves_the_payment_waiting(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    body = event("payment_intent.payment_failed", reference, status="something_new")
    assert post(auth_client, body).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.PENDING


def test_other_event_types_are_acknowledged_and_ignored(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    assert post(auth_client, event("charge.refunded", reference)).status_code == 200
    assert post(auth_client, {"type": "ping"}).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.PENDING


def test_a_bad_signature_is_refused_and_changes_nothing(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    body = event("payment_intent.succeeded", reference)

    forged = sign(json.dumps(body).encode(), secret="whsec_" + "z" * 32)
    for header in (forged, "", "t=1,v1=00"):
        assert post(auth_client, body, header=header).status_code == 400
    assert auth_client.post(WEBHOOK_URL, content=json.dumps(body)).status_code == 400

    assert load(db_session, reference).status is TransactionStatus.PENDING
    assert tickets(db_session, reference) == 0


@pytest.mark.parametrize("header", ODD_HEADERS)
def test_an_odd_signature_header_answers_400_and_not_500(auth_client, header):
    response = post(auth_client, {"type": "ping"}, header=header)

    assert response.status_code == 400


@pytest.mark.parametrize("payload", [b"not json", b"[1, 2]", b'"text"'])
def test_a_signed_payload_that_is_not_an_event_is_refused(auth_client, payload):
    assert post(auth_client, payload).status_code == 400


def test_without_a_configured_secret_the_endpoint_says_so(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    assert post(auth_client, {"type": "ping"}).status_code == 503


def test_only_bad_signatures_count_against_the_rate_limit(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE", 2)
    reference = start_payment(auth_client, email_sender, db_session)

    for _ in range(5):  # a burst of good events from Stripe is never turned away
        body = event("payment_intent.succeeded", reference)
        assert post(auth_client, body).status_code == 200

    codes = [post(auth_client, {"type": "ping"}, header="t=1,v1=00").status_code]
    codes += [post(auth_client, {"type": "ping"}, header="t=1,v1=00").status_code]
    codes += [post(auth_client, {"type": "ping"}, header="t=1,v1=00").status_code]
    assert codes == [400, 400, 429]


def test_a_body_over_the_size_limit_is_refused_before_anything_is_read(
    auth_client, monkeypatch
):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 2048)
    payload = b'{"type":"ping","pad":"' + b"x" * 4096 + b'"}'

    assert post(auth_client, payload).status_code == 413


# --- a refund made at Stripe (its dashboard) ---------------------------------------


def charge_event(*, intent_id=INTENT, reference=None, **charge):
    data = {
        "id": "ch_1",
        "object": "charge",
        "payment_intent": intent_id,
        "currency": "eur",
        "amount": AMOUNT,
        "amount_refunded": AMOUNT,
        "refunded": True,
        "metadata": {"reference": reference} if reference else {},
        **charge,
    }
    return {"id": "evt_2", "type": "charge.refunded", "data": {"object": data}}


def confirmed_payment(auth_client, email_sender, db_session) -> str:
    reference = start_payment(auth_client, email_sender, db_session)
    assert (
        post(auth_client, event("payment_intent.succeeded", reference)).status_code
        == 200
    )
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    return reference


def ticket_status(db_session, reference) -> PaymentStatus:
    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == reference)
    )
    db_session.refresh(ticket)
    return ticket.payment_status


def test_a_full_refund_at_stripe_cancels_the_ticket_and_closes_the_payment(
    auth_client, email_sender, db_session, gateway, caplog
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(auth_client, charge_event())

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.REFUNDED
    assert ticket_status(db_session, reference) is PaymentStatus.CANCELLED
    assert f"Payment {reference} was refunded at Stripe" in caplog.text


def test_the_seat_is_free_again_after_a_refund_at_stripe(
    auth_client, email_sender, db_session, gateway
):
    confirmed_payment(auth_client, email_sender, db_session)
    assert post(auth_client, charge_event()).status_code == 200

    again = auth_client.post(INITIATE_URL, json=INITIATE)

    assert again.status_code == 201  # the person can buy again


def test_a_repeated_refund_event_changes_nothing(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    assert post(auth_client, charge_event()).status_code == 200
    assert post(auth_client, charge_event()).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.REFUNDED
    assert ticket_status(db_session, reference) is PaymentStatus.CANCELLED


def test_the_refund_event_of_our_own_refund_command_changes_nothing(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.status = TransactionStatus.REFUNDED  # what ``refund`` leaves behind
    db_session.commit()

    assert post(auth_client, charge_event()).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.REFUNDED


def test_the_whole_amount_refunded_counts_even_without_the_refunded_flag(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(auth_client, charge_event(refunded=False, amount_refunded=AMOUNT))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.REFUNDED


@pytest.mark.parametrize("refunded_cents", [1, AMOUNT // 2, AMOUNT - 1, 0, None])
def test_a_partial_refund_leaves_the_ticket_alone_and_says_so(
    auth_client, email_sender, db_session, gateway, caplog, refunded_cents
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(
        auth_client,
        charge_event(refunded=False, amount_refunded=refunded_cents),
    )

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert ticket_status(db_session, reference) is not PaymentStatus.CANCELLED
    assert "partly refunded" in caplog.text


def test_a_refund_closes_a_payment_that_was_waiting_for_a_refund(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.status = TransactionStatus.REFUND_DUE
    db_session.commit()

    assert post(auth_client, charge_event()).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.REFUNDED


@pytest.mark.parametrize(
    "local",
    [TransactionStatus.PENDING, TransactionStatus.EXPIRED, TransactionStatus.FAILED],
)
def test_a_refund_before_we_confirmed_stops_a_late_confirmation_from_giving_a_ticket(
    auth_client, email_sender, db_session, gateway, local
):
    reference = start_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.status = local
    db_session.commit()

    assert post(auth_client, charge_event()).status_code == 200
    assert load(db_session, reference).status is TransactionStatus.REFUNDED

    # The ``succeeded`` event arrives late: the money already went back.
    assert (
        post(auth_client, event("payment_intent.succeeded", reference)).status_code
        == 200
    )
    assert load(db_session, reference).status is TransactionStatus.REFUNDED
    assert tickets(db_session, reference) == 0


def test_the_ticket_of_another_payment_of_the_same_person_is_never_touched(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    # An earlier payment of the same person that was refunded at Stripe.
    old = load(db_session, reference)
    other = Transaction(
        reference="ENEI-OLD0000001",
        user_id=old.user_id,
        ticket_tier_id=old.ticket_tier_id,
        amount_cents=AMOUNT,
        quantity=1,
        phone="912345678",
        provider="stripe",
        provider_reference="pi_old",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        status=TransactionStatus.CONFIRMED,
    )
    db_session.add(other)
    db_session.commit()

    assert post(auth_client, charge_event(intent_id="pi_old")).status_code == 200

    assert load(db_session, "ENEI-OLD0000001").status is TransactionStatus.REFUNDED
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert ticket_status(db_session, reference) is not PaymentStatus.CANCELLED


def test_the_refund_of_a_charge_of_another_site_on_the_account_is_ignored(
    auth_client, email_sender, db_session, gateway, caplog
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(auth_client, charge_event(intent_id="pi_someoneelse"))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert "not one of our payments" in caplog.text


def test_a_refund_of_a_payment_made_through_another_provider_is_ignored(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.provider = "ifthenpay"
    db_session.commit()

    assert post(auth_client, charge_event()).status_code == 200

    assert load(db_session, reference).status is TransactionStatus.CONFIRMED


def test_a_charge_for_another_amount_than_ours_is_left_alone_and_logged(
    auth_client, email_sender, db_session, gateway, caplog
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(auth_client, charge_event(amount=AMOUNT + 100))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
    assert "needs a look" in caplog.text


def test_a_refund_event_before_the_intent_id_is_saved_is_found_by_reference(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)
    transaction = load(db_session, reference)
    transaction.provider_reference = None
    db_session.commit()

    response = post(auth_client, charge_event(reference=reference))

    assert response.status_code == 200
    transaction = load(db_session, reference)
    assert transaction.status is TransactionStatus.REFUNDED
    assert transaction.provider_reference == INTENT


@pytest.mark.parametrize("intent_id", [None, 123, {"id": INTENT}])
def test_a_refund_event_without_a_usable_payment_intent_is_acknowledged(
    auth_client, email_sender, db_session, gateway, intent_id
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(auth_client, charge_event(intent_id=intent_id))

    assert response.status_code == 200
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED


def test_a_refund_event_with_a_bad_signature_changes_nothing(
    auth_client, email_sender, db_session, gateway
):
    reference = confirmed_payment(auth_client, email_sender, db_session)

    response = post(
        auth_client, charge_event(), header=sign(b"{}", secret="whsec_other")
    )

    assert response.status_code == 400
    assert load(db_session, reference).status is TransactionStatus.CONFIRMED
