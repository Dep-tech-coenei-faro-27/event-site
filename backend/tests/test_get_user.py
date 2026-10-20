from app.core.qr import verify_qr_payload
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.tickets.service import confirm_ticket_payment_and_issue_qr
from tests.helpers import LOGIN_URL, authenticate, register_and_verify

USERS_ME_URL = "/api/users/me"


def test_get_users_me_requires_authentication(auth_client, email_sender):
    register_and_verify(
        auth_client,
        email_sender,
        name="Ana Silva",
        email="ana@example.com",
        password="Password123!",
    )

    assert auth_client.get(USERS_ME_URL).status_code == 401


def test_get_users_me_returns_the_profile_after_login(auth_client, email_sender):
    email = "ana@example.com"
    register_and_verify(auth_client, email_sender, email=email, password="Password123!")

    login_response = auth_client.post(
        LOGIN_URL, json={"email": email, "password": "Password123!"}
    )
    assert login_response.status_code == 200

    response = auth_client.get(USERS_ME_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == email
    assert body["name"] == "Ana Silva"
    assert body["qr_code"] is None


def test_get_users_me_exposes_the_qr_code_after_payment(
    auth_client, email_sender, db_session
):
    user = authenticate(auth_client, email_sender, db_session)

    ticket = Ticket(user_id=user.id, transaction_reference="ENEI-QRTEST0001")
    db_session.add(ticket)
    db_session.commit()

    response = auth_client.get(USERS_ME_URL)
    assert response.status_code == 200
    assert response.json()["qr_code"] is None

    confirmed = confirm_ticket_payment_and_issue_qr(db_session, ticket.id)
    assert confirmed.payment_status is PaymentStatus.PAID

    response = auth_client.get(USERS_ME_URL)
    assert response.status_code == 200
    qr_code = response.json()["qr_code"]
    assert qr_code == confirmed.qr_payload
    assert verify_qr_payload(qr_code).ticket_id == ticket.id


def test_put_users_me_still_updates_the_profile(auth_client, email_sender, db_session):
    authenticate(auth_client, email_sender, db_session)

    response = auth_client.put(USERS_ME_URL, json={"name": "Ana Maria"})

    assert response.status_code == 200
    assert response.json()["name"] == "Ana Maria"


def test_get_users_me_ignores_a_cancelled_ticket(auth_client, email_sender, db_session):
    user = authenticate(auth_client, email_sender, db_session)
    cancelled = Ticket(
        user_id=user.id,
        transaction_reference="ENEI-CANCELLED1",
        payment_status=PaymentStatus.CANCELLED,
        qr_payload="old-cancelled-qr",
    )
    db_session.add(cancelled)
    db_session.commit()

    assert auth_client.get("/api/users/me").json()["qr_code"] is None


def test_get_users_me_shows_the_new_ticket_after_a_cancelled_one(
    auth_client, email_sender, db_session
):
    user = authenticate(auth_client, email_sender, db_session)
    db_session.add(
        Ticket(
            user_id=user.id,
            transaction_reference="ENEI-CANCELLED1",
            payment_status=PaymentStatus.CANCELLED,
            qr_payload="old-cancelled-qr",
        )
    )
    db_session.commit()
    current = Ticket(user_id=user.id, transaction_reference="ENEI-CURRENT001")
    db_session.add(current)
    db_session.commit()
    confirm_ticket_payment_and_issue_qr(db_session, current.id)
    db_session.refresh(current)

    assert auth_client.get("/api/users/me").json()["qr_code"] == current.qr_payload
