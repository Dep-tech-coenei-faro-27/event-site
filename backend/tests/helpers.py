import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME
from app.domains.payments.models import Ticket, TicketTier
from app.domains.payments.tiers import TIER_SPECS
from app.domains.users.models import User

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
ME_URL = "/api/auth/me"
VERIFY_URL = "/api/auth/verify-email"

INITIATE_URL = "/api/payment/initiate"

TOKEN_QUERY = re.compile(r"[?&]token=([A-Za-z0-9._\-]+)")

DEFAULT_TEST_PRICES = {
    TicketTier.ACESSO: 2000,
    TicketTier.REFEICOES: 3000,
    TicketTier.COMPLETO: 4500,
    TicketTier.GERAL: 5000,
}


def transaction_url(reference: str) -> str:
    return f"/api/payment/transactions/{reference}"


def register_user(
    auth_client,
    email_sender,
    *,
    name="Ana Silva",
    email="ana@example.com",
    password="Password123!",
    accept_terms=True,
):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": name,
            "email": email,
            "password": password,
            "accept_terms": accept_terms,
        },
    )
    assert response.status_code == 201
    return response


def extract_verification_token(email_sender) -> str:
    assert email_sender.sent
    link = TOKEN_QUERY.search(email_sender.sent[-1]["html_body"])
    assert link is not None
    return link.group(1)


def register_and_verify(
    auth_client,
    email_sender,
    *,
    name="Ana Silva",
    email="ana@example.com",
    password="Password123!",
):
    register_user(auth_client, email_sender, name=name, email=email, password=password)
    token = extract_verification_token(email_sender)
    response = auth_client.post(VERIFY_URL, json={"token": token})
    assert response.status_code == 200
    return response


def user_id_of(db_session, email="ana@example.com") -> int:
    return db_session.scalar(select(User.id).where(User.email == email))


def access_claims(user_id, token_version=0):
    now = datetime.now(UTC)
    return {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "tv": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }


def encode_claims(claims) -> str:
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def authenticate(
    auth_client,
    email_sender,
    db_session,
    *,
    email="ana@example.com",
    password="Password123!",
) -> User:
    """Register, verify and log a user in by attaching a valid access cookie."""
    register_and_verify(auth_client, email_sender, email=email, password=password)
    user = db_session.scalar(select(User).where(User.email == email))
    auth_client.cookies.set(
        ACCESS_COOKIE_NAME, encode_claims(access_claims(user.id, user.token_version))
    )
    return user


def seed_ticket_tiers(db_session) -> dict[TicketTier, Ticket]:
    """Insert the four ticket modalities with deterministic test prices."""
    tickets: dict[TicketTier, Ticket] = {}
    for tier, spec in TIER_SPECS.items():
        ticket = Ticket(
            tier=tier,
            name=spec.name,
            price_cents=DEFAULT_TEST_PRICES[tier],
            is_student=spec.is_student,
            inventory_limit=None,
        )
        db_session.add(ticket)
        tickets[tier] = ticket
    db_session.commit()
    for ticket in tickets.values():
        db_session.refresh(ticket)
    return tickets
