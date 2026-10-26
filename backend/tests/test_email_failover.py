"""The second SMTP server: when it takes over, when it does not, and what it sends."""

import logging
import os
import smtplib
import threading
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailDeliveryError, EmailSender, factory
from app.core.email import outbox as outbox_module
from app.core.email.failover import (
    FALLBACK,
    PRIMARY,
    FailoverEmailSender,
    reserve_primary,
    usage_on,
)
from app.core.email.models import EmailOutbox, EmailStatus, EmailTransportUsage
from app.core.email.outbox import (
    delete_old_emails,
    deliver_due,
    enqueue_email,
    queue_stats,
)
from app.core.email.smtp import SmtpEmailSender, classify_error
from app.core.email.templates import TICKET_QR_CID, build_ticket_email
from app.core.qr import generate_qr_payload, render_qr_png
from tests.test_config import make_prod
from tests.test_email_service import _make_server, _RecordingServer

requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="row locks require PostgreSQL",
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
QUOTA = smtplib.SMTPDataError(550, b"5.4.5 Daily sending quota exceeded")
RECIPIENT = smtplib.SMTPRecipientsRefused(
    {"ana@example.com": (550, b"5.1.1 User unknown")}
)


class Transport(EmailSender):
    def __init__(self, error: Exception | None = None) -> None:
        self.sent: list[tuple[str, dict]] = []
        self.error = error

    def send_html(self, to_email, subject, html_body, **extras) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((to_email, extras))


def _delivery_error(cause: Exception) -> EmailDeliveryError:
    return EmailDeliveryError("could not send", classify_error(cause))


class Clock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def db(test_engine):
    with Session(bind=test_engine) as session:
        session.query(EmailOutbox).delete()
        session.query(EmailTransportUsage).delete()
        session.commit()
        yield session
        session.rollback()
        session.query(EmailOutbox).delete()
        session.query(EmailTransportUsage).delete()
        session.commit()


def _failover(test_engine, primary, fallback, clock=None, daily_limit=0):
    return FailoverEmailSender(
        primary,
        fallback,
        lambda: Session(bind=test_engine),
        daily_limit=daily_limit,
        clock=clock or Clock(),
    )


# Classifying what the server answered


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (QUOTA, "limit"),
        (smtplib.SMTPDataError(450, b"4.7.28 Rate limited, try later"), "limit"),
        (
            smtplib.SMTPRecipientsRefused(
                {"ana@example.com": (452, b"Too many emails sent today")}
            ),
            "limit",
        ),
        (
            smtplib.SMTPSenderRefused(
                550, b"You have exceeded your daily limit", "no-reply@example.com"
            ),
            "limit",
        ),
        (RECIPIENT, "recipient"),
        (
            smtplib.SMTPRecipientsRefused(
                {"ana@example.com": (553, b"5.1.3 Invalid address")}
            ),
            "recipient",
        ),
        (smtplib.SMTPDataError(552, b"5.3.4 Message size exceeds limit"), "server"),
        (smtplib.SMTPServerDisconnected("Connection unexpectedly closed"), "server"),
        (smtplib.SMTPAuthenticationError(535, b"Invalid credentials"), "server"),
        (smtplib.SMTPDataError(451, b"4.3.0 Local error in processing"), "server"),
        (smtplib.SMTPConnectError(421, b"Service not available"), "server"),
        (ConnectionRefusedError(111, "Connection refused"), "server"),
        (TimeoutError("timed out"), "server"),
    ],
)
def test_each_smtp_failure_is_classified(error, kind):
    assert classify_error(error) == kind


class _RefusingServer(_RecordingServer):
    error: Exception = QUOTA

    def send_message(self, message):
        raise self.error


@pytest.mark.parametrize(
    ("error", "kind"), [(QUOTA, "limit"), (RECIPIENT, "recipient")]
)
def test_the_smtp_sender_says_what_kind_of_failure_it_was(monkeypatch, error, kind):
    _RefusingServer.error = error
    monkeypatch.setattr(smtplib, "SMTP_SSL", _make_server([], _RefusingServer))
    sender = SmtpEmailSender("smtp.example.com", 465, "", "", "no-reply@example.com")

    with pytest.raises(EmailDeliveryError) as raised:
        sender.send_html("ana@example.com", "Olá", "<p>x</p>")

    assert raised.value.kind == kind
    assert "ana@example.com" not in str(raised.value)


# Which server sends


def test_the_primary_sends_while_it_can(db, test_engine):
    primary, fallback = Transport(), Transport()

    _failover(test_engine, primary, fallback).send_html("a@example.com", "s", "<p/>")

    assert [to for to, _ in primary.sent] == ["a@example.com"]
    assert fallback.sent == []
    assert usage_on(db, NOW.date())["primary_sent_today"] == 1


def test_a_quota_refusal_moves_to_the_fallback_until_midnight_utc(db, test_engine):
    primary = Transport(_delivery_error(QUOTA))
    fallback = Transport()
    clock = Clock(datetime(2026, 10, 20, 23, 59, tzinfo=UTC))
    sender = _failover(test_engine, primary, fallback, clock)

    sender.send_html("a@example.com", "s", "<p/>")
    primary.error = None  # the primary would accept again, but its day is over
    sender.send_html("b@example.com", "s", "<p/>")

    assert [to for to, _ in fallback.sent] == ["a@example.com", "b@example.com"]
    assert primary.sent == []
    usage = usage_on(db, date(2026, 10, 20))
    assert usage["primary_exhausted_today"] is True
    assert usage["fallback_sent_today"] == 2

    clock.now = datetime(2026, 10, 21, 0, 0, tzinfo=UTC)
    sender.send_html("c@example.com", "s", "<p/>")

    assert [to for to, _ in primary.sent] == ["c@example.com"]


def test_the_day_is_the_utc_day_and_not_the_local_one(db, test_engine):
    primary = Transport(_delivery_error(QUOTA))
    fallback = Transport()
    # 00:30 in Lisbon summer time is still 23:30 of the day before in UTC.
    clock = Clock(datetime(2026, 7, 21, 0, 30, tzinfo=ZoneInfo("Europe/Lisbon")))
    sender = _failover(test_engine, primary, fallback, clock)

    sender.send_html("a@example.com", "s", "<p/>")

    assert usage_on(db, date(2026, 7, 20))["primary_exhausted_today"] is True
    assert usage_on(db, date(2026, 7, 21))["primary_exhausted_today"] is False


def test_a_server_failure_sends_that_email_by_the_fallback_only(db, test_engine):
    primary = Transport(
        _delivery_error(smtplib.SMTPServerDisconnected("Connection closed"))
    )
    fallback = Transport()
    sender = _failover(test_engine, primary, fallback)

    sender.send_html("a@example.com", "s", "<p/>")
    primary.error = None
    sender.send_html("b@example.com", "s", "<p/>")

    assert [to for to, _ in fallback.sent] == ["a@example.com"]
    assert [to for to, _ in primary.sent] == ["b@example.com"]
    usage = usage_on(db, NOW.date())
    assert usage == {
        "primary_sent_today": 1,
        "primary_exhausted_today": False,
        "fallback_sent_today": 1,
    }


def test_an_unexpected_error_of_the_primary_also_goes_to_the_fallback(test_engine, db):
    primary, fallback = Transport(OSError("network is unreachable")), Transport()

    _failover(test_engine, primary, fallback).send_html("a@example.com", "s", "<p/>")

    assert [to for to, _ in fallback.sent] == ["a@example.com"]


def test_a_refused_recipient_never_goes_to_the_fallback(db, test_engine):
    primary, fallback = Transport(_delivery_error(RECIPIENT)), Transport()

    with pytest.raises(EmailDeliveryError) as raised:
        _failover(test_engine, primary, fallback).send_html(
            "ana@example.com", "s", "<p/>"
        )

    assert raised.value.kind == "recipient"
    assert fallback.sent == []
    assert usage_on(db, NOW.date()) == {
        "primary_sent_today": 0,
        "primary_exhausted_today": False,
        "fallback_sent_today": 0,
    }


def test_the_daily_limit_moves_to_the_fallback_before_the_provider_refuses(
    db, test_engine
):
    primary, fallback = Transport(), Transport()
    clock = Clock()
    sender = _failover(test_engine, primary, fallback, clock, daily_limit=2)

    for name in "abc":
        sender.send_html(f"{name}@example.com", "s", "<p/>")

    assert [to for to, _ in primary.sent] == ["a@example.com", "b@example.com"]
    assert [to for to, _ in fallback.sent] == ["c@example.com"]

    clock.now = NOW + timedelta(days=1)
    sender.send_html("d@example.com", "s", "<p/>")

    assert primary.sent[-1][0] == "d@example.com"


def test_when_both_fail_the_queue_retries_the_email(db, test_engine):
    primary = Transport(_delivery_error(QUOTA))
    fallback = Transport(_delivery_error(smtplib.SMTPServerDisconnected("closed")))
    sender = _failover(test_engine, primary, fallback)
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)

    report = deliver_due(db, sender, now=NOW)

    assert report.retried == 1
    db.refresh(row)
    assert row.status == EmailStatus.PENDING
    assert row.attempts == 1
    assert "ana@example.com" not in (row.last_error or "")

    fallback.error = None
    report = deliver_due(db, sender, now=NOW + timedelta(hours=1))

    assert report.sent == 1
    assert [to for to, _ in fallback.sent] == ["ana@example.com"]


def test_the_switch_is_logged_once_and_without_the_address(db, test_engine, caplog):
    primary, fallback = Transport(_delivery_error(QUOTA)), Transport()
    sender = _failover(test_engine, primary, fallback)

    with caplog.at_level(logging.WARNING, logger="app.core.email.failover"):
        for name in ("ana", "rui", "eva"):
            sender.send_html(f"{name}@example.com", "s", "<p/>")

    warnings = [r.getMessage() for r in caplog.records]
    assert len(warnings) == 1
    assert "fallback" in warnings[0] and "midnight UTC" in warnings[0]


def test_a_server_failure_is_logged_with_a_masked_address(db, test_engine, caplog):
    primary = Transport(_delivery_error(smtplib.SMTPServerDisconnected("closed")))
    sender = _failover(test_engine, primary, Transport())

    with caplog.at_level(logging.WARNING, logger="app.core.email.failover"):
        sender.send_html("ana.silva@example.com", "s", "<p/>")

    assert "ana.silva@example.com" not in caplog.text
    assert "a***@example.com" in caplog.text


# What the fallback sends


def _ticket(monkeypatch, payload: str, primary_error: Exception | None):
    """Send the ticket through ``build_transport`` and return what each server got."""
    primary_servers, fallback_servers = [], []

    class Primary(_RecordingServer):
        def send_message(self, message):
            if primary_error is not None:
                raise primary_error
            super().send_message(message)

    def connect(host, port, timeout=None, context=None):
        servers = primary_servers if host == "smtp.one.example" else fallback_servers
        server_cls = Primary if host == "smtp.one.example" else _RecordingServer
        return _make_server(servers, server_cls)(host, port, timeout, context)

    monkeypatch.setattr(smtplib, "SMTP_SSL", connect)
    for name, value in {
        "SMTP_HOST": "smtp.one.example",
        "SMTP_PORT": 465,
        "SMTP_USER": "",
        "EMAIL_SENDER": "noreply@one.example",
        "SMTP2_HOST": "smtp.two.example",
        "SMTP2_PORT": 465,
        "SMTP2_USER": "",
        "SMTP2_EMAIL_SENDER": "",
    }.items():
        monkeypatch.setattr(settings, name, value)

    html, text = build_ticket_email("Ana Silva", "Passe geral", "ENEI-ABC")
    factory.build_transport().send_html(
        "ana@example.com",
        "Bilhete",
        html,
        {TICKET_QR_CID: render_qr_png(payload)},
        text_body=text,
    )
    return primary_servers, fallback_servers


def _shape(message):
    """The tree of parts with their content, without the random boundaries."""
    if message.is_multipart():
        return (
            message.get_content_type(),
            [_shape(part) for part in message.iter_parts()],
        )
    return (
        message.get_content_type(),
        message.get("Content-ID"),
        message.get_content(),
    )


def test_the_ticket_email_is_the_same_through_both_servers(
    db, test_engine, monkeypatch
):
    monkeypatch.setattr(factory, "SessionLocal", lambda: Session(bind=test_engine))

    payload = generate_qr_payload(7)
    by_primary, _ = _ticket(monkeypatch, payload, None)
    db.query(EmailTransportUsage).delete()
    db.commit()
    tried, by_fallback = _ticket(monkeypatch, payload, QUOTA)

    first = by_primary[0].sent_message
    second = by_fallback[0].sent_message
    assert tried[0].sent_message is None  # the primary was asked and refused
    assert second.get_content_type() == "multipart/alternative"
    assert _shape(second) == _shape(first)
    for header in ("Subject", "From", "To"):
        assert second[header] == first[header]


def test_the_fallback_can_send_from_its_own_address(db, test_engine, monkeypatch):
    monkeypatch.setattr(factory, "SessionLocal", lambda: Session(bind=test_engine))
    monkeypatch.setattr(settings, "SMTP2_EMAIL_SENDER", "noreply@two.example")
    servers = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", _make_server(servers))
    for name, value in {
        "SMTP_HOST": "smtp.one.example",
        "SMTP_PORT": 465,
        "SMTP2_HOST": "smtp.two.example",
        "SMTP2_PORT": 465,
    }.items():
        monkeypatch.setattr(settings, name, value)

    transport = factory.build_transport()

    assert isinstance(transport, FailoverEmailSender)
    assert transport.primary.from_email == settings.EMAIL_SENDER
    assert transport.fallback.from_email == "noreply@two.example"


def test_without_a_second_server_the_transport_is_the_plain_smtp(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.one.example")
    monkeypatch.setattr(settings, "SMTP2_HOST", "")

    assert isinstance(factory.build_transport(), SmtpEmailSender)


def test_production_refuses_an_unencrypted_second_server():
    with pytest.raises(ValidationError, match="SMTP2_SECURITY"):
        make_prod(SMTP2_HOST="smtp.two.example", SMTP2_SECURITY="none")


def test_the_daily_limit_cannot_be_negative():
    with pytest.raises(ValidationError, match="SMTP_DAILY_LIMIT"):
        make_prod(SMTP_DAILY_LIMIT=-1)


# Status and housekeeping


def test_the_status_shows_and_warns_when_the_fallback_sent(
    db, test_engine, monkeypatch, capsys
):
    monkeypatch.setattr(
        "app.db.session.SessionLocal", lambda: Session(bind=test_engine)
    )
    today = datetime.now(UTC)
    sender = _failover(
        test_engine, Transport(_delivery_error(QUOTA)), Transport(), Clock(today)
    )
    sender.send_html("a@example.com", "s", "<p/>")

    stats = queue_stats(db, now=today)
    outbox_module.main(["--status"])
    out = capsys.readouterr().out

    assert stats["fallback_sent_today"] == 1
    assert stats["primary_exhausted_today"] is True
    assert "WARNING: the fallback SMTP sent 1 emails today" in out
    assert "midnight UTC" in out


def test_the_status_has_no_warning_while_the_primary_sends(
    db, test_engine, monkeypatch, capsys
):
    monkeypatch.setattr(
        "app.db.session.SessionLocal", lambda: Session(bind=test_engine)
    )

    outbox_module.main(["--status"])

    assert "WARNING" not in capsys.readouterr().out


def test_old_daily_counts_are_deleted(db):
    today = datetime.now(UTC).date()
    db.add_all(
        [
            EmailTransportUsage(transport=PRIMARY, day=today, sent=5),
            EmailTransportUsage(
                transport=FALLBACK, day=today - timedelta(days=31), sent=3
            ),
        ]
    )
    db.commit()

    delete_old_emails(db)

    assert [row.day for row in db.query(EmailTransportUsage)] == [today]


# Several workers at once


@requires_postgres
def test_two_workers_never_go_past_the_daily_limit(db, test_engine):
    limit, workers = 5, 20
    barrier = threading.Barrier(workers)
    results: list[bool] = []
    lock = threading.Lock()

    def take():
        with Session(bind=test_engine) as session:
            barrier.wait()
            got = reserve_primary(session, NOW.date(), limit)
        with lock:
            results.append(got)

    threads = [threading.Thread(target=take) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(True) == limit
    assert usage_on(db, NOW.date())["primary_sent_today"] == limit


@requires_postgres
def test_workers_that_hit_the_quota_together_all_end_on_the_fallback(db, test_engine):
    workers = 8
    barrier = threading.Barrier(workers)
    fallback = Transport()
    errors: list[Exception] = []

    class Refusing(EmailSender):
        def send_html(self, *args, **kwargs):
            barrier.wait()
            raise _delivery_error(QUOTA)

    sender = _failover(test_engine, Refusing(), fallback)

    def send(index):
        try:
            sender.send_html(f"p{index}@example.com", "s", "<p/>")
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=send, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(fallback.sent) == workers
    assert usage_on(db, NOW.date()) == {
        "primary_sent_today": 0,
        "primary_exhausted_today": True,
        "fallback_sent_today": workers,
    }
