"""End-to-end test of the whole purchase, against the real server (issue #281).

Talks HTTP to a running backend (uvicorn) and reads its database, which must be a
throwaway one created by the migrations. For each of the five modalities a new
person registers, reads the verification link from the queued email, verifies,
logs in, starts an MB WAY payment, gets it confirmed by the simulated provider, finds
a QR that verifies in ``GET /users/me`` and the ticket email in the queue, and logs
out (the old session then answers 401). Then the failures: a payment that expires
frees its seat, a sold-out modality answers 409, and so does a second purchase,
also when two arrive at the same moment.

No sleeping and no waiting on the wall clock: the simulated provider keeps no state
and measures time from the instant written inside its payment reference, so the
script moves that instant (and our deadline) into the past to make time pass.

Run from ``backend/``, with the same environment as the server::

    E2E_DISPOSABLE_DB=<database> uv run python -m tests.e2e.full_flow

It refuses to run unless the database is named in ``E2E_DISPOSABLE_DB``, the server
is in ``dev`` with ``PAYMENTS_MODE=simulated`` and the confirming simulator, and no
mail server is configured (emails stay in the queue and in the log). See
``docs/testes-e2e.md``.
"""

import json
import os
import re
import secrets
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib import error, request

from sqlalchemy import func, select

import app.db.models  # noqa: F401  (every table, for the foreign keys)
from app.core.config import settings
from app.core.email.console import ConsoleEmailSender
from app.core.email.factory import build_transport
from app.core.email.models import EmailOutbox
from app.core.email.templates import TICKET_EMAIL_SUBJECT, VERIFICATION_EMAIL_SUBJECT
from app.core.qr import verify_qr_payload
from app.core.security import ACCESS_COOKIE_NAME
from app.db.session import SessionLocal
from app.domains.payments.gateway import SimulatedMBWayGateway
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.service import generate_reference
from app.domains.payments.set_price import set_price
from app.domains.tickets.models import Ticket
from app.domains.users.models import User

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
MAX_SECONDS = 120
PHONE = "912345678"
PRICES = {
    TicketTier.ACESSO: 2000,
    TicketTier.REFEICOES: 3000,
    TicketTier.COMPLETO: 4500,
    TicketTier.GERAL: 5000,
    TicketTier.GERAL_REFEICOES: 6500,
}
STUDENT_TIERS = (TicketTier.ACESSO, TicketTier.REFEICOES, TicketTier.COMPLETO)
TOKEN_QUERY = re.compile(r"[?&]token=([A-Za-z0-9._\-]+)")
# A different run on the same database must not meet this run's accounts.
RUN = secrets.token_hex(4)


class FlowError(AssertionError):
    pass


def check(condition: bool, step: str, detail: object = "") -> None:
    if not condition:
        raise FlowError(f"{step}: {detail}" if detail != "" else step)


@dataclass
class Response:
    status: int
    body: object
    cookie: str | None


def call(
    method: str, path: str, body: dict | None = None, cookie: str | None = None
) -> Response:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=15) as resp:
            status, raw, response_headers = resp.status, resp.read(), resp.headers
    except error.HTTPError as exc:
        status, raw, response_headers = exc.code, exc.read(), exc.headers
    except (error.URLError, TimeoutError) as exc:
        raise FlowError(f"{method} {path}: no answer from the server ({exc})") from exc
    # The session cookie is ``Secure``: a cookie jar would not send it over plain
    # http, so it is carried by hand.
    session = None
    for header in response_headers.get_all("Set-Cookie") or []:
        name_value = header.split(";", 1)[0]
        if name_value.startswith(f"{ACCESS_COOKIE_NAME}="):
            session = name_value
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = raw[:200]
    return Response(status, parsed, session)


def expect(response: Response, status: int, step: str) -> Response:
    detail = response.body.get("detail") if isinstance(response.body, dict) else ""
    check(
        response.status == status,
        step,
        f"expected HTTP {status}, got {response.status} {detail!r}",
    )
    return response


@dataclass
class Person:
    label: str
    student: bool
    email: str = ""
    password: str = field(default_factory=lambda: f"E2e-{secrets.token_hex(8)}A1!")
    cookie: str | None = None

    def __post_init__(self) -> None:
        domain = settings.STUDENT_EMAIL_DOMAINS[0] if self.student else "example.com"
        self.email = f"e2e-{RUN}-{self.label}@{domain}"

    def get(self, path: str) -> Response:
        return call("GET", path, cookie=self.cookie)

    def post(self, path: str, body: dict | None = None) -> Response:
        return call("POST", path, body, cookie=self.cookie)

    def buy(self, tier: TicketTier, phone: str = PHONE) -> Response:
        return self.post(
            "/api/payment/initiate", {"ticket_tier": tier.value, "phone": phone}
        )


# --- database: read what the server queued, and make time pass ------------------


def queued_emails(email: str, subject: str) -> list[EmailOutbox]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(EmailOutbox)
                .where(EmailOutbox.to_email == email, EmailOutbox.subject == subject)
                .order_by(EmailOutbox.id)
            )
        )


def verification_token(person: Person) -> str:
    emails = queued_emails(person.email, VERIFICATION_EMAIL_SUBJECT)
    check(len(emails) == 1, "one verification email queued", len(emails))
    match = TOKEN_QUERY.search(emails[0].html_body)
    check(match is not None, "verification email carries a link with a token")
    return match.group(1)


def make_time_pass(reference: str, seconds: int) -> None:
    """Move a payment ``seconds`` into the past, at the provider and at our end.

    The simulated provider reads the creation instant from ``SIM-<instant>-<ref>``;
    ``expires_at`` is the deadline the backend keeps.
    """
    with SessionLocal() as db:
        transaction = db.scalar(
            select(Transaction).where(Transaction.reference == reference)
        )
        check(transaction is not None, "payment exists in the database", reference)
        prefix, instant, rest = transaction.provider_reference.split("-", 2)
        transaction.provider_reference = f"{prefix}-{int(instant) - seconds}-{rest}"
        transaction.expires_at = transaction.expires_at - timedelta(seconds=seconds)
        db.commit()


def ticket_of(reference: str) -> Ticket | None:
    with SessionLocal() as db:
        return db.scalar(
            select(Ticket).where(Ticket.transaction_reference == reference)
        )


def seats_taken() -> int:
    """The seats taken, all modalities together (the stock is one)."""
    with SessionLocal() as db:
        return db.scalar(
            select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
                Transaction.status.in_(
                    (TransactionStatus.CONFIRMED, TransactionStatus.PENDING)
                ),
            )
        )


def fill_stock_leaving(
    seats_left: int, tier: TicketTier, owner: "Person"
) -> int | None:
    """Take every seat but ``seats_left`` with one filler payment; return its id.

    The server reads TICKET_STOCK_LIMIT from its own environment, so the test cannot
    lower it; it fills the stock instead. ``release_filler`` gives the seats back.
    """
    missing = settings.TICKET_STOCK_LIMIT - seats_left - seats_taken()
    check(missing >= 0, "the stock has room for the test", f"missing={missing}")
    if missing == 0:
        return None
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == owner.email))
        price = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == tier))
        now = datetime.now(UTC)
        filler = Transaction(
            reference=generate_reference(db),
            user_id=user.id,
            ticket_tier_id=price.id,
            amount_cents=PRICES[tier],
            quantity=missing,
            status=TransactionStatus.CONFIRMED,
            phone="910000001",
            provider="simulated",
            expires_at=now + timedelta(hours=1),
            confirmed_at=now,
        )
        db.add(filler)
        db.commit()
        return filler.id


def release_filler(filler_id: int | None) -> None:
    if filler_id is None:
        return
    with SessionLocal() as db:
        row = db.get(Transaction, filler_id)
        row.status = TransactionStatus.REFUNDED
        db.commit()


def tier_available(tier: TicketTier) -> bool:
    tiers = expect(call("GET", "/api/payment/tiers"), 200, "list the modalities").body
    return next(row["available"] for row in tiers if row["tier"] == tier.value)


# --- the steps -------------------------------------------------------------------


def preflight() -> None:
    """Refuse to run anywhere a registration could reach a person or real data."""
    disposable = os.environ.get("E2E_DISPOSABLE_DB", "")
    check(
        disposable != "" and disposable == settings.POSTGRES_DB,
        "E2E_DISPOSABLE_DB must name the throwaway database (POSTGRES_DB)",
    )
    check(settings.ENVIRONMENT == "dev", "ENVIRONMENT must be dev")
    check(not settings.SMTP_HOST, "SMTP_HOST must be empty: no email may leave")
    check(
        isinstance(build_transport(), ConsoleEmailSender),
        "emails must only go to the log",
    )
    check(settings.PAYMENTS_MODE == "simulated", "PAYMENTS_MODE must be simulated")
    check(
        0
        < settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS
        < settings.MBWAY_PAYMENT_TIMEOUT_SECONDS,
        "the simulator must confirm before the payment window ends "
        "(PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS)",
    )
    check(
        settings.PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS == 0,
        "PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS must be 0 (every poll asks)",
    )
    check(settings.STUDENT_EMAIL_DOMAINS, "STUDENT_EMAIL_DOMAINS needs a domain")
    expect(call("GET", "/api/health/ready"), 200, "server is up and ready")


def open_ticket_office() -> None:
    with SessionLocal() as db:
        for tier in TicketTier:
            set_price(db, tier, PRICES[tier])
    tiers = expect(call("GET", "/api/payment/tiers"), 200, "list the modalities").body
    check(
        all(row["sale_open"] and row["available"] for row in tiers),
        "every modality is on sale",
        tiers,
    )


def sign_up(person: Person) -> None:
    body = {
        "name": "Pessoa Teste",
        "email": person.email,
        "password": person.password,
        "accept_terms": True,
    }
    created = expect(call("POST", "/api/auth/register", body), 201, "register").body
    check(created["is_verified"] is False, "a new account is not verified")
    expected = "verified" if person.student else "none"
    check(
        created["student_verification_status"] == expected,
        "student status from the email domain",
        created["student_verification_status"],
    )

    login = {"email": person.email, "password": person.password}
    expect(
        call("POST", "/api/auth/login", login), 403, "login before verifying the email"
    )

    token = verification_token(person)
    expect(
        call("POST", "/api/auth/verify-email", {"token": token[:-4] + "AAAA"}),
        400,
        "verify with a tampered token",
    )
    expect(call("POST", "/api/auth/verify-email", {"token": token}), 200, "verify")
    expect(
        call("POST", "/api/auth/verify-email", {"token": token}),
        200,
        "verify again (idempotent)",
    )

    expect(
        call("POST", "/api/auth/login", {**login, "password": "Wrong-pass1!"}),
        401,
        "login with a wrong password",
    )
    session = expect(call("POST", "/api/auth/login", login), 200, "login")
    check(session.cookie is not None, "login sets the session cookie")
    person.cookie = session.cookie
    me = expect(person.get("/api/users/me"), 200, "profile after login").body
    check(me["is_verified"] is True, "the account is verified")
    check(me["qr_code"] is None, "no QR before paying")


def pay(person: Person, tier: TicketTier) -> str:
    started = expect(person.buy(tier), 201, f"start the payment ({tier.value})").body
    check(started["status"] == "pending", "a new payment waits", started["status"])
    check(started["amount_cents"] == PRICES[tier], "price", started["amount_cents"])
    reference = started["reference"]

    url = f"/api/payment/transactions/{reference}"
    status = expect(person.get(url), 200, "payment status").body["status"]
    check(status == "pending", "the provider has not confirmed yet", status)
    me = expect(person.get("/api/users/me"), 200, "profile while paying").body
    check(me["qr_code"] is None, "no QR while the payment waits")
    check(
        me["pending_payment"] and me["pending_payment"]["reference"] == reference,
        "the profile shows the payment that waits",
    )
    expect(person.buy(tier), 409, "a second payment while one waits")

    make_time_pass(reference, settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS)
    confirmed = expect(person.get(url), 200, "payment status after the delay").body
    check(
        confirmed["status"] == "confirmed",
        "the simulated provider confirms",
        confirmed["status"],
    )
    return reference


def check_ticket(person: Person, tier: TicketTier, reference: str) -> None:
    ticket = ticket_of(reference)
    check(ticket is not None, "the payment issued a ticket")
    me = expect(person.get("/api/users/me"), 200, "profile after paying").body
    check(me["qr_code"] is not None, "GET /users/me has the QR")
    check(
        verify_qr_payload(me["qr_code"]).ticket_id == ticket.id,
        "the QR is signed for this ticket",
    )
    check(me["ticket"]["tier"] == tier.value, "the ticket's modality", me["ticket"])
    check(me["pending_payment"] is None, "nothing waits any more")

    emails = queued_emails(person.email, TICKET_EMAIL_SUBJECT)
    check(len(emails) == 1, "one ticket email queued", len(emails))
    check(emails[0].dedupe_key == f"ticket:{ticket.id}", "the email is this ticket's")
    check(emails[0].inline_images, "the ticket email carries the QR image")

    for other in (tier, TicketTier.GERAL):
        expect(person.buy(other), 409, "a second purchase after the ticket")


def log_out(person: Person) -> None:
    old_session = person.cookie
    expect(person.post("/api/auth/logout"), 200, "logout")
    person.cookie = old_session
    expect(person.get("/api/users/me"), 401, "the old session after logout")
    person.cookie = None


def full_purchase(tier: TicketTier) -> None:
    person = Person(tier.value.replace("_", "-"), student=tier in STUDENT_TIERS)
    sign_up(person)
    reference = pay(person, tier)
    check_ticket(person, tier, reference)
    log_out(person)


def wrong_inputs() -> None:
    person = Person("inputs", student=False)
    sign_up(person)
    expect(
        person.buy(TicketTier.ACESSO), 403, "a student modality without student status"
    )
    expect(person.buy(TicketTier.GERAL, phone="12345"), 422, "an invalid phone")
    expect(
        person.post("/api/payment/initiate", {"ticket_tier": "vip", "phone": PHONE}),
        422,
        "an unknown modality",
    )
    expect(
        person.get("/api/payment/transactions/ENEI-0000000000"),
        404,
        "someone else's or a missing payment",
    )
    log_out(person)


def expired_payment_frees_the_seat() -> None:
    tier = TicketTier.GERAL_REFEICOES
    late, waiting, last = (Person(n, student=False) for n in ("late", "wait", "last"))
    for person in (late, waiting, last):
        sign_up(person)

    filler = fill_stock_leaving(1, tier, late)
    try:
        _last_seat(tier, late, waiting, last)
    finally:
        release_filler(filler)


def _last_seat(
    tier: TicketTier, late: "Person", waiting: "Person", last: "Person"
) -> None:
    check(tier_available(tier), "one seat left")
    held = expect(
        late.buy(tier, phone=SimulatedMBWayGateway.UNPAID_PHONE),
        201,
        "take the last seat (a payment never approved)",
    ).body["reference"]
    check(not tier_available(tier), "a waiting payment holds the last seat")
    expect(waiting.buy(tier), 409, "sold out while the payment waits")

    make_time_pass(held, settings.MBWAY_PAYMENT_TIMEOUT_SECONDS + 1)
    reference = expect(
        waiting.buy(tier), 201, "the expired payment freed the seat"
    ).body["reference"]
    status = expect(
        late.get(f"/api/payment/transactions/{held}"), 200, "expired payment"
    ).body["status"]
    check(status == "expired", "the unapproved payment expired", status)
    check(ticket_of(held) is None, "an expired payment issues no ticket")
    me = expect(late.get("/api/users/me"), 200, "profile after expiring").body
    check(me["qr_code"] is None and me["pending_payment"] is None, "nothing left")

    make_time_pass(reference, settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS)
    status = expect(
        waiting.get(f"/api/payment/transactions/{reference}"), 200, "status"
    ).body["status"]
    check(status == "confirmed", "the freed seat was sold", status)
    check(not tier_available(tier), "the modality is sold out")
    expect(last.buy(tier), 409, "buy a sold-out modality")


def simultaneous_purchases() -> None:
    """Two purchases by the same person at the same moment: exactly one goes on."""
    person = Person("twice", student=False)
    sign_up(person)
    barrier = threading.Barrier(2)
    results: list[int] = []

    def buy() -> None:
        barrier.wait()
        results.append(person.buy(TicketTier.GERAL).status)

    threads = [threading.Thread(target=buy) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    check(sorted(results) == [201, 409], "one purchase at a time", results)


STEPS: list[tuple[str, Callable[[], None]]] = [
    ("preflight", preflight),
    ("open the ticket office", open_ticket_office),
    *(
        (f"full purchase: {tier.value}", lambda tier=tier: full_purchase(tier))
        for tier in TicketTier
    ),
    ("wrong inputs", wrong_inputs),
    ("expired payment frees the seat; sold out", expired_payment_frees_the_seat),
    ("simultaneous purchases", simultaneous_purchases),
]


def main() -> int:
    started = time.monotonic()
    for name, step in STEPS:
        try:
            step()
        except FlowError as exc:
            print(f"FAILED  {name}: {exc}")
            return 1
        print(f"OK      {name}")
    elapsed = time.monotonic() - started
    if elapsed > MAX_SECONDS:
        print(f"FAILED  took {elapsed:.0f} s, more than {MAX_SECONDS} s")
        return 1
    print(f"End-to-end flow: all OK in {elapsed:.1f} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
