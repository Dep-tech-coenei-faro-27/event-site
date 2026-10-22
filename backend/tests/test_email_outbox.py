import os
import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.email import EmailDeliveryError, EmailSender
from app.core.email import outbox as outbox_module
from app.core.email.models import EmailOutbox, EmailStatus
from app.core.email.outbox import (
    BATCH_SIZE,
    RETRY_DELAYS_SECONDS,
    OutboxEmailSender,
    OutboxWorker,
    delete_emails_for,
    delete_old_emails,
    deliver_due,
    enqueue_email,
    queue_stats,
    requeue_failed,
)

requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="SKIP LOCKED requires PostgreSQL",
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


class Transport(EmailSender):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.error: Exception | None = None

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((to_email, subject, html_body))


@pytest.fixture
def db(test_engine):
    with Session(bind=test_engine) as session:
        session.query(EmailOutbox).delete()
        session.commit()
        yield session
        session.rollback()
        session.query(EmailOutbox).delete()
        session.commit()


def _utc(value: datetime) -> datetime:
    """SQLite returns naive UTC; PostgreSQL returns the session time zone."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _row(db: Session, email_id: int) -> EmailOutbox:
    db.expire_all()
    return db.scalar(select(EmailOutbox).where(EmailOutbox.id == email_id))


def test_enqueue_stores_a_pending_email(db):
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>Oi</p>", now=NOW)

    assert row.status == EmailStatus.PENDING
    assert row.attempts == 0
    assert row.html_body == "<p>Oi</p>"


def test_a_due_email_is_sent_and_its_body_is_cleared(db):
    transport = Transport()
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>link</p>", now=NOW)

    report = deliver_due(db, transport, now=NOW)

    assert (report.sent, report.retried, report.failed) == (1, 0, 0)
    assert transport.sent == [("ana@example.com", "Olá", "<p>link</p>")]
    stored = _row(db, row.id)
    assert stored.status == EmailStatus.SENT
    assert stored.sent_at is not None
    assert stored.html_body == ""


def test_a_sent_email_is_not_sent_again(db):
    transport = Transport()
    enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)

    deliver_due(db, transport, now=NOW)
    deliver_due(db, transport, now=NOW + timedelta(hours=1))

    assert len(transport.sent) == 1


def test_an_email_that_is_not_due_yet_waits(db):
    transport = Transport()
    enqueue_email(
        db, "ana@example.com", "Olá", "<p>x</p>", now=NOW + timedelta(hours=1)
    )

    report = deliver_due(db, transport, now=NOW)

    assert report.sent == 0
    assert transport.sent == []


def test_a_failure_is_retried_later_with_a_growing_delay(db):
    transport = Transport()
    transport.error = EmailDeliveryError("mail server unreachable")
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)

    when = NOW
    for attempt, delay in enumerate(RETRY_DELAYS_SECONDS[:3], start=1):
        report = deliver_due(db, transport, now=when)
        assert report.retried == 1
        stored = _row(db, row.id)
        assert stored.status == EmailStatus.PENDING
        assert stored.attempts == attempt
        expected = when + timedelta(seconds=delay)
        assert _utc(stored.next_attempt_at) == expected
        # Not due before the delay passes.
        assert deliver_due(db, transport, now=when + timedelta(seconds=1)).retried == 0
        when = expected


def test_the_email_goes_out_once_the_provider_recovers(db):
    transport = Transport()
    transport.error = EmailDeliveryError("down")
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)
    deliver_due(db, transport, now=NOW)

    transport.error = None
    later = NOW + timedelta(seconds=RETRY_DELAYS_SECONDS[0] + 1)
    report = deliver_due(db, transport, now=later)

    assert report.sent == 1
    assert _row(db, row.id).status == EmailStatus.SENT


def test_it_gives_up_after_the_maximum_attempts(db):
    transport = Transport()
    transport.error = EmailDeliveryError("down")
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)

    when = NOW
    last = None
    for _ in range(3):
        last = deliver_due(db, transport, now=when, max_attempts=3)
        when += timedelta(days=1)

    assert last.failed == 1
    stored = _row(db, row.id)
    assert stored.status == EmailStatus.FAILED
    assert stored.attempts == 3
    # Once failed it is left alone.
    assert deliver_due(db, transport, now=when, max_attempts=3).retried == 0


def test_the_error_never_keeps_the_recipient(db):
    transport = Transport()
    transport.error = EmailDeliveryError("rejected ana.silva@example.com")
    row = enqueue_email(db, "ana.silva@example.com", "Olá", "<p>x</p>", now=NOW)

    deliver_due(db, transport, now=NOW)

    error = _row(db, row.id).last_error
    assert "ana.silva@example.com" not in error
    assert "a***@example.com" in error


def test_a_worker_that_restarts_picks_up_what_was_left_pending(db):
    # A "restart" is a new worker with a new transport reading the same table.
    enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)

    new_transport = Transport()
    report = deliver_due(db, new_transport, now=NOW + timedelta(minutes=5))

    assert report.sent == 1
    assert len(new_transport.sent) == 1


def test_an_email_being_sent_by_another_worker_is_not_taken(db):
    row = enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>", now=NOW)
    row.locked_until = NOW + timedelta(seconds=60)
    db.commit()
    transport = Transport()

    assert deliver_due(db, transport, now=NOW).sent == 0

    # A crashed worker's lease expires and the email is taken again.
    assert deliver_due(db, transport, now=NOW + timedelta(seconds=61)).sent == 1


def test_the_same_dedupe_key_queues_one_email(db):
    first = enqueue_email(db, "ana@example.com", "Bilhete", "<p>1</p>", dedupe_key="t1")
    second = enqueue_email(
        db, "ana@example.com", "Bilhete", "<p>2</p>", dedupe_key="t1"
    )

    assert second.id == first.id
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == 1


def test_the_sender_only_queues_and_wakes_the_worker(db, test_engine):
    wake = threading.Event()
    sender = OutboxEmailSender(lambda: Session(bind=test_engine), wake=wake)

    sender.send_html("ana@example.com", "Olá", "<p>x</p>")

    assert wake.is_set()
    rows = db.scalars(select(EmailOutbox)).all()
    assert [(r.to_email, r.status) for r in rows] == [
        ("ana@example.com", EmailStatus.PENDING)
    ]


def test_the_sender_reports_when_it_cannot_queue():
    def broken():
        raise RuntimeError("database is down")

    sender = OutboxEmailSender(broken)

    with pytest.raises(EmailDeliveryError):
        sender.send_html("ana@example.com", "Olá", "<p>x</p>")


def test_the_worker_thread_delivers_a_queued_email(db, test_engine):
    transport = Transport()
    enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>")
    worker = OutboxWorker(
        lambda: Session(bind=test_engine), transport, poll_seconds=0.05
    )

    worker.start()
    try:
        worker.wake.set()
        for _ in range(100):
            if transport.sent:
                break
            threading.Event().wait(0.05)
    finally:
        worker.stop()

    assert len(transport.sent) == 1


def test_old_rows_are_deleted(db):
    old_sent = enqueue_email(db, "a@example.com", "x", "", now=NOW)
    old_sent.status = EmailStatus.SENT
    old_sent.sent_at = datetime.now(UTC) - timedelta(days=8)
    recent_sent = enqueue_email(db, "b@example.com", "x", "")
    recent_sent.status = EmailStatus.SENT
    recent_sent.sent_at = datetime.now(UTC) - timedelta(days=1)
    pending = enqueue_email(db, "c@example.com", "x", "<p>keep</p>")
    db.commit()

    assert delete_old_emails(db) == 1

    left = {r.id for r in db.scalars(select(EmailOutbox)).all()}
    assert left == {recent_sent.id, pending.id}


@requires_postgres
def test_two_workers_at_the_same_time_never_send_the_same_email_twice(db, test_engine):
    for number in range(30):
        enqueue_email(db, f"user{number}@example.com", f"Email {number}", "<p>x</p>")

    lock = threading.Lock()
    sent: list[str] = []

    class Counting(EmailSender):
        def send_html(self, to_email: str, subject: str, html_body: str) -> None:
            threading.Event().wait(0.01)
            with lock:
                sent.append(to_email)

    def worker() -> None:
        with Session(bind=test_engine) as session:
            for _ in range(10):
                deliver_due(session, Counting(), limit=5)

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len(sent) == 30
    assert len(set(sent)) == 30


def test_the_worker_drains_a_backlog_without_waiting_between_batches(db, test_engine):
    total = BATCH_SIZE * 2 + 5
    for number in range(total):
        enqueue_email(db, f"user{number}@example.com", f"Email {number}", "<p>x</p>")
    transport = Transport()
    # A long poll: if the worker waited between batches this would time out.
    worker = OutboxWorker(lambda: Session(bind=test_engine), transport, poll_seconds=60)

    worker.start()
    try:
        worker.wake.set()
        for _ in range(100):
            if len(transport.sent) == total:
                break
            threading.Event().wait(0.05)
    finally:
        worker.stop()

    assert len(transport.sent) == total


def _failed(db: Session, address: str, *, age_days: float, body: str = "<p>x</p>"):
    row = enqueue_email(db, address, "Falhou", body)
    row.status = EmailStatus.FAILED
    row.attempts = 10
    row.created_at = datetime.now(UTC) - timedelta(days=age_days)
    db.commit()
    return row


def test_failed_emails_can_be_put_back_in_the_queue(db):
    retry = _failed(db, "a@example.com", age_days=0.1)
    blanked = _failed(db, "b@example.com", age_days=3, body="")

    assert requeue_failed(db) == 1

    assert _row(db, retry.id).status == EmailStatus.PENDING
    assert _row(db, retry.id).attempts == 0
    assert _row(db, blanked.id).status == EmailStatus.FAILED
    transport = Transport()
    assert deliver_due(db, transport).sent == 1


def test_a_failed_email_loses_its_body_after_a_day_and_the_row_after_a_month(db):
    fresh = _failed(db, "a@example.com", age_days=0.5)
    stale = _failed(db, "b@example.com", age_days=3)
    ancient = _failed(db, "c@example.com", age_days=40)
    fresh_id, stale_id, ancient_id = fresh.id, stale.id, ancient.id

    assert delete_old_emails(db) == 1

    assert _row(db, fresh_id).html_body == "<p>x</p>"
    assert _row(db, stale_id).html_body == ""
    assert _row(db, ancient_id) is None


def test_every_row_of_an_address_can_be_erased(db):
    enqueue_email(db, "Ana@Example.com", "1", "<p>a</p>")
    enqueue_email(db, "ana@example.com", "2", "<p>b</p>")
    other = enqueue_email(db, "rui@example.com", "3", "<p>c</p>")

    assert delete_emails_for(db, "ana@example.com") == 2

    assert [r.id for r in db.scalars(select(EmailOutbox)).all()] == [other.id]


def test_the_queue_statistics_show_the_backlog(db):
    enqueue_email(db, "a@example.com", "1", "<p>x</p>", now=NOW)
    sent = enqueue_email(db, "b@example.com", "2", "<p>x</p>", now=NOW)
    sent.status = EmailStatus.SENT
    db.commit()

    stats = queue_stats(db, now=datetime.now(UTC) + timedelta(seconds=90))

    assert (stats["pending"], stats["sent"], stats["failed"]) == (1, 1, 0)
    assert stats["oldest_pending_seconds"] >= 90


def test_the_command_delivers_shows_and_requeues(db, test_engine, monkeypatch, capsys):
    transport = Transport()
    monkeypatch.setattr(
        "app.db.session.SessionLocal", lambda: Session(bind=test_engine)
    )
    monkeypatch.setattr("app.core.email.factory.build_transport", lambda: transport)
    enqueue_email(db, "ana@example.com", "Olá", "<p>x</p>")
    _failed(db, "rui@example.com", age_days=0.1)

    outbox_module.main([])
    assert "Sent 1" in capsys.readouterr().out
    assert transport.sent[0][0] == "ana@example.com"

    outbox_module.main(["--status"])
    assert "oldest_pending_seconds" in capsys.readouterr().out

    outbox_module.main(["--requeue-failed"])
    assert "Requeued 1" in capsys.readouterr().out


def test_the_app_starts_and_stops_the_worker_with_the_server(monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.core.email import factory
    from app.main import app

    calls: list[str] = []

    class FakeWorker:
        def start(self):
            calls.append("start")

        def stop(self):
            calls.append("stop")

    monkeypatch.setattr(settings, "EMAIL_OUTBOX_WORKER", True)
    monkeypatch.setattr(factory, "_build_worker", lambda: FakeWorker())

    with TestClient(app):
        assert calls == ["start"]

    assert calls == ["start", "stop"]


def test_the_worker_can_be_switched_off(monkeypatch):
    from app.core.config import settings
    from app.core.email import factory

    created = []
    monkeypatch.setattr(settings, "EMAIL_OUTBOX_WORKER", False)
    monkeypatch.setattr(factory, "_build_worker", lambda: created.append(1))

    factory.start_email_worker()

    assert created == []


@requires_postgres
def test_two_requests_with_the_same_dedupe_key_queue_one_email(db, test_engine):
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def queue() -> None:
        with Session(bind=test_engine) as session:
            try:
                barrier.wait(timeout=10)
                enqueue_email(
                    session, "ana@example.com", "Bilhete", "<p>x</p>", dedupe_key="b1"
                )
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

    threads = [threading.Thread(target=queue) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert errors == []
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == 1


class ImageTransport(EmailSender):
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, bytes] | None]] = []

    def send_html(self, to_email, subject, html_body, inline_images=None):
        self.sent.append((to_email, inline_images))


def test_inline_images_reach_the_transport_and_are_cleared_once_sent(db):
    png = b"\x89PNG\r\n\x1a\nfake"
    row = enqueue_email(
        db,
        "a@example.com",
        "Bilhete",
        '<img src="cid:ticket-qr" />',
        inline_images={"ticket-qr": png},
        now=NOW,
    )
    transport = ImageTransport()

    deliver_due(db, transport, now=NOW)

    assert transport.sent == [("a@example.com", {"ticket-qr": png})]
    db.refresh(row)
    assert row.status == EmailStatus.SENT
    assert row.inline_images is None


def test_failed_rows_lose_their_inline_images_with_the_body(db):
    row = enqueue_email(
        db, "a@example.com", "x", "<p>qr</p>", inline_images={"qr": b"\x89PNG"}
    )
    row.status = EmailStatus.FAILED
    row.created_at = datetime.now(UTC) - timedelta(days=2)
    db.commit()

    delete_old_emails(db)

    db.refresh(row)
    assert row.html_body == ""
    assert not row.inline_images
