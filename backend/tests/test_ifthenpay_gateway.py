import logging

import pytest

from app.domains.payments.gateway import (
    IfThenPayMBWayGateway,
    PaymentGatewayError,
    UnrecognisedStatusError,
)
from app.domains.payments.models import TransactionStatus


def build_gateway(*, post_response=None, get_response=None):
    posted: list[tuple] = []
    fetched: list[tuple] = []

    def fake_post(url, payload, headers):
        posted.append((url, payload, headers))
        return post_response

    def fake_get(url, headers):
        fetched.append((url, headers))
        return get_response

    gateway = IfThenPayMBWayGateway(
        mbway_key="MBW-123456",
        base_url="https://api.ifthenpay.com/spg/payment/mbway",
        timeout_seconds=10,
        http_post=fake_post,
        http_get=fake_get,
    )
    return gateway, posted, fetched


def test_create_accepts_only_the_success_code_and_returns_the_request_id():
    gateway, posted, _ = build_gateway(
        post_response={
            "Status": "000",
            "Message": "Pending",
            "RequestId": "itp-42",
            "Amount": "50.00",
            "OrderId": "ENEI-0000000001",
        }
    )

    payment = gateway.create_payment(
        reference="ENEI-0000000001",
        amount_cents=5000,
        phone="912345678",
        email="ana@example.com",
        description="ENEI - Passe geral",
    )

    assert payment.provider_reference == "itp-42"
    assert payment.status is TransactionStatus.PENDING
    assert posted[0][1]["amount"] == "50.00"


@pytest.mark.parametrize("code", ["999", "100", "122", "-1"])
def test_create_rejects_every_non_success_code(code):
    gateway, _, _ = build_gateway(post_response={"Status": code, "Message": "rejected"})

    with pytest.raises(PaymentGatewayError, match="refused"):
        gateway.create_payment(
            reference="ENEI-0000000001",
            amount_cents=5000,
            phone="912345678",
            email="ana@example.com",
            description="ENEI - Passe geral",
        )


def test_create_fails_when_the_success_response_has_no_request_id():
    gateway, _, _ = build_gateway(post_response={"Status": "000"})

    with pytest.raises(PaymentGatewayError, match="RequestId"):
        gateway.create_payment(
            reference="ENEI-0000000001",
            amount_cents=5000,
            phone="912345678",
            email="ana@example.com",
            description="ENEI - Passe geral",
        )


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("000", TransactionStatus.CONFIRMED),
        ("123", TransactionStatus.PENDING),
        ("020", TransactionStatus.FAILED),
        ("101", TransactionStatus.EXPIRED),
        ("122", TransactionStatus.FAILED),
    ],
)
def test_status_query_maps_the_documented_codes(code, expected):
    gateway, _, fetched = build_gateway(get_response={"Status": code})

    status = gateway.get_status(
        reference="ENEI-0000000001", provider_reference="itp-42"
    )

    assert status is expected
    assert "requestId=itp-42" in fetched[0][0]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (101, TransactionStatus.EXPIRED),
        (" 101 ", TransactionStatus.EXPIRED),
        (123, TransactionStatus.PENDING),
        ("000 ", TransactionStatus.CONFIRMED),
    ],
)
def test_status_query_reads_the_code_as_text_or_as_a_number(code, expected):
    gateway, _, _ = build_gateway(get_response={"Status": code})

    status = gateway.get_status(
        reference="ENEI-0000000001", provider_reference="itp-42"
    )

    assert status is expected


@pytest.mark.parametrize(
    "answer",
    [
        {"Status": "777"},
        {"Status": "0101"},
        {"Status": "EXPIRED"},
        {"Status": ""},
        {"Status": None},
        {"Status": True},
        {"Message": "no status here"},
        {},
    ],
)
def test_status_query_does_not_mistake_an_unreadable_answer_for_waiting(answer, caplog):
    """A waiting payment keeps its seat, so an unreadable answer is an error."""
    gateway, _, _ = build_gateway(get_response=answer)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(UnrecognisedStatusError):
            gateway.get_status(reference="ENEI-0000000001", provider_reference="itp-42")

    assert "unrecognised status" in caplog.text


def test_status_query_without_a_request_id_stays_pending_and_does_not_call_out():
    gateway, _, fetched = build_gateway(get_response={"Status": "000"})

    status = gateway.get_status(reference="ENEI-0000000001", provider_reference=None)

    assert status is TransactionStatus.PENDING
    assert fetched == []
