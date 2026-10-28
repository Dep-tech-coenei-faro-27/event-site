import hashlib
import logging
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.config import Settings, settings
from app.domains.auth import router as auth_router
from app.domains.auth import service
from app.domains.auth.events import hash_ip
from app.domains.auth.models import ResetPasswordToken
from app.domains.users.models import User
from app.domains.users.service import (
    ResetTokenUsedError,
    get_user_by_email,
    reset_user_password,
    update_user_password,
)
from tests.helpers import LOGIN_URL, TOKEN_QUERY, register_and_verify
from tests.test_auth import FORGOT_PASSWORD_URL
from tests.test_password import CHANGE_PASSWORD_URL, RESET_PASSWORD_URL

CD_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "cd.yml"

EMAIL = "ana@example.com"
PASSWORD = "Password123!"
NEW_PASSWORD = "NewPassword123!"
SHARED_IP = "203.0.113.50"

requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="row-level locking requires PostgreSQL",
)


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(rate_limit, "current_time", lambda: 1000)


def as_ip(monkeypatch, address):
    monkeypatch.setattr(auth_router, "client_ip", lambda request: address)


def login(auth_client, email=EMAIL, password=PASSWORD):
    return auth_client.post(LOGIN_URL, json={"email": email, "password": password})


def request_reset_token(auth_client, email_sender):
    assert auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL}).status_code
    return TOKEN_QUERY.search(email_sender.sent[-1]["html_body"]).group(1)


def test_300_students_on_5_shared_ips_are_not_blocked_by_the_production_limits(
    auth_client, db_session, monkeypatch, clock
):
    production_limits = {
        name: field.default
        for name, field in Settings.model_fields.items()
        if name.startswith("RATE_LIMIT_LOGIN")
    }
    for name, value in production_limits.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    # 300 bcrypt checks would take over a minute; the limits are what is tested.
    monkeypatch.setattr(service, "verify_password", lambda pw, hashed: hashed == pw)
    emails = [f"student{number}@example.com" for number in range(300)]
    db_session.add_all(
        User(name="Estudante", email=email, password_hash=PASSWORD, is_verified=True)
        for email in emails
    )
    db_session.commit()

    statuses = []
    for number, email in enumerate(emails):
        as_ip(monkeypatch, f"198.51.100.{number % 5}")
        statuses.append(login(auth_client, email).status_code)

    assert statuses == [200] * 300


def test_one_account_with_five_failures_is_limited_on_a_shared_ip(
    auth_client, email_sender, monkeypatch
):
    register_and_verify(auth_client, email_sender)
    as_ip(monkeypatch, SHARED_IP)

    failures = [
        login(auth_client, password="Wrong-Passw0rd!").status_code for _ in range(5)
    ]
    right_password = login(auth_client)
    other_student = login(auth_client, "rui@example.com", "Wrong-Passw0rd!")

    assert failures == [401] * 5
    assert right_password.status_code == 429
    assert other_student.status_code == 401


def test_the_login_limit_per_ip_read_from_the_environment_takes_effect(
    auth_client, monkeypatch
):
    monkeypatch.setenv("RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE", "3")
    from_environment = Settings(
        _env_file=None,
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="password",
        POSTGRES_DB="db",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
    )
    monkeypatch.setattr(auth_router, "settings", from_environment)
    as_ip(monkeypatch, SHARED_IP)

    statuses = [
        login(auth_client, f"user{number}@example.com", "Wrong-Passw0rd!").status_code
        for number in range(5)
    ]

    assert statuses == [401, 401, 401, 429, 429]


def _login_limit_block() -> str:
    workflow = CD_WORKFLOW.read_text()
    block = re.search(
        r"^ *if \[ -n \"\$\{\{ vars\.RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE \}\}\" \];"
        r" then\n.*?\n *fi\n",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    assert block, "cd.yml does not pass RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE"
    return block.group(0)


@pytest.mark.parametrize(("variable", "written"), [("120", True), ("", False)])
def test_the_deploy_writes_the_login_limit_only_when_the_variable_exists(
    tmp_path, variable, written
):
    script = _login_limit_block().replace(
        "${{ vars.RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE }}", variable
    )

    subprocess.run(["sh", "-c", script], cwd=tmp_path, check=True)

    env_file = tmp_path / ".env"
    content = env_file.read_text() if env_file.exists() else ""
    expected = "RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE=120\n" if written else ""
    assert content == expected


def test_the_deploy_does_not_write_the_login_limit_unconditionally():
    workflow = CD_WORKFLOW.read_text()
    unconditional = re.findall(
        r"^ *RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE=", workflow, re.MULTILINE
    )

    assert unconditional == []


def test_changing_the_password_closes_a_reset_link_already_asked_for(
    auth_client, email_sender, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    register_and_verify(auth_client, email_sender)
    token = request_reset_token(auth_client, email_sender)
    login(auth_client)

    changed = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    reset = auth_client.post(
        RESET_PASSWORD_URL, json={"token": token, "new_password": "Another123!Pass"}
    )

    assert changed.status_code == 200
    assert reset.status_code == 400
    assert reset.json()["detail"] == "Password reset token has already been used"
    assert login(auth_client, password=NEW_PASSWORD).status_code == 200
    assert login(auth_client, password="Another123!Pass").status_code == 401


def test_a_reset_link_asked_for_after_the_change_still_works(
    auth_client, email_sender, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    token = request_reset_token(auth_client, email_sender)

    reset = auth_client.post(
        RESET_PASSWORD_URL, json={"token": token, "new_password": "Another123!Pass"}
    )

    assert reset.status_code == 200


@requires_postgres
def test_a_reset_racing_a_password_change_loses(
    auth_client, email_sender, db_session, test_engine, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    register_and_verify(auth_client, email_sender)
    request_reset_token(auth_client, email_sender)
    user_id = get_user_by_email(db_session, EMAIL).id
    changing = threading.Event()
    release = threading.Event()
    outcome: list[object] = []

    def change() -> None:
        session = Session(bind=test_engine)
        real_commit = session.commit

        def held_commit() -> None:
            changing.set()
            assert release.wait(timeout=10)
            real_commit()

        session.commit = held_commit
        try:
            update_user_password(session, session.get(User, user_id), NEW_PASSWORD)
        finally:
            session.close()

    def reset() -> None:
        session = Session(bind=test_engine)
        try:
            token = session.scalar(select(ResetPasswordToken))
            reset_user_password(
                session, session.get(User, user_id), "Another123!Pass", token
            )
            outcome.append("reset won")
        except ResetTokenUsedError as exc:
            outcome.append(exc)
        finally:
            session.close()

    changer = threading.Thread(target=change)
    changer.start()
    assert changing.wait(timeout=10)
    resetter = threading.Thread(target=reset)
    resetter.start()
    resetter.join(timeout=1)
    release.set()
    changer.join(timeout=10)
    resetter.join(timeout=10)

    assert len(outcome) == 1 and isinstance(outcome[0], ResetTokenUsedError)
    db_session.expire_all()
    assert login(auth_client, password=NEW_PASSWORD).status_code == 200


def auth_events(caplog) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.auth.events"
    ]


def test_authentication_events_are_logged_with_the_id_and_a_hashed_ip(
    auth_client, email_sender, db_session, monkeypatch, caplog
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    register_and_verify(auth_client, email_sender)
    user_id = get_user_by_email(db_session, EMAIL).id
    as_ip(monkeypatch, SHARED_IP)
    ip_hash = hash_ip(SHARED_IP)
    caplog.set_level(logging.INFO)

    login(auth_client, password="Wrong-Passw0rd!")
    login(auth_client, "nobody@example.com", "Wrong-Passw0rd!")
    login(auth_client)
    auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    token = request_reset_token(auth_client, email_sender)
    auth_client.post(
        RESET_PASSWORD_URL, json={"token": token, "new_password": "Another123!Pass"}
    )

    assert auth_events(caplog) == [
        f"auth_event=login_failed user_id={user_id} ip_hash={ip_hash}"
        " detail=invalid_credentials",
        f"auth_event=login_failed user_id=- ip_hash={ip_hash}"
        " detail=invalid_credentials",
        f"auth_event=login_succeeded user_id={user_id} ip_hash={ip_hash} detail=-",
        f"auth_event=password_changed user_id={user_id} ip_hash={ip_hash}"
        " detail=change",
        f"auth_event=password_changed user_id={user_id} ip_hash={ip_hash} detail=reset",
    ]


def test_a_login_of_an_unverified_account_is_logged_as_a_failure(
    auth_client, email_sender, monkeypatch, caplog
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    auth_client.post(
        "/api/auth/register",
        json={
            "name": "Ana Silva",
            "email": EMAIL,
            "password": PASSWORD,
            "accept_terms": True,
        },
    )
    caplog.set_level(logging.INFO, logger="app.auth.events")

    assert login(auth_client).status_code == 403

    [event] = auth_events(caplog)
    assert event.startswith("auth_event=login_failed user_id=")
    assert event.endswith(" detail=email_not_verified")


def test_the_logs_have_no_email_password_or_ip(
    auth_client, email_sender, monkeypatch, caplog
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    register_and_verify(auth_client, email_sender)
    as_ip(monkeypatch, SHARED_IP)
    caplog.set_level(logging.DEBUG)

    login(auth_client, "Ana@Example.com", "Wrong-Passw0rd!")
    login(auth_client, "nobody@example.com", "Wrong-Passw0rd!")
    login(auth_client)
    auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    token = request_reset_token(auth_client, email_sender)
    auth_client.post(
        RESET_PASSWORD_URL, json={"token": token, "new_password": "Another123!Pass"}
    )

    logged = "\n".join(record.getMessage() for record in caplog.records).lower()
    assert auth_events(caplog)
    for secret in (
        "ana@example.com",
        "nobody@example.com",
        PASSWORD.lower(),
        NEW_PASSWORD.lower(),
        "wrong-passw0rd!",
        "another123!pass",
        SHARED_IP,
        token.lower(),
    ):
        assert secret not in logged


def test_the_ip_hash_is_keyed_and_stable():
    plain = hashlib.sha256(SHARED_IP.encode()).hexdigest()[:16]

    assert hash_ip(SHARED_IP) == hash_ip(SHARED_IP)
    assert hash_ip(SHARED_IP) != hash_ip("203.0.113.51")
    assert hash_ip(SHARED_IP) != plain
    assert len(hash_ip(SHARED_IP)) == 16
