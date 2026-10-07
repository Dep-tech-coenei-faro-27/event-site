import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import rate_limit
from app.core.config import Settings, settings
from app.core.rate_limit import RateLimit, client_ip, enforce_rate_limit
from app.main import app
from tests.helpers import LOGIN_URL, REGISTER_URL, register_and_verify
from tests.test_password import CHANGE_PASSWORD_URL

RESEND_URL = "/api/auth/resend-verification-email"
FORGOT_URL = "/api/auth/forgot-password"

THREE_PER_MINUTE = (RateLimit("test", 3, 60),)


@pytest.fixture
def clock(monkeypatch):
    now = {"value": 1000}
    monkeypatch.setattr(rate_limit, "current_time", lambda: now["value"])
    return now


def count_rows(db_session) -> int:
    return db_session.execute(text("SELECT COUNT(*) FROM rate_limits")).scalar()


def test_attempts_within_the_limit_are_allowed(db_session, clock):
    for _ in range(3):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")


def test_attempt_over_the_limit_is_blocked_with_retry_after(db_session, clock):
    for _ in range(3):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")

    with pytest.raises(HTTPException) as error:
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "60"


def test_retry_after_counts_down_inside_the_window(db_session, clock):
    for _ in range(3):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")
    clock["value"] += 45

    with pytest.raises(HTTPException) as error:
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")

    assert error.value.headers["Retry-After"] == "15"


def test_limit_resets_after_the_window(db_session, clock):
    for _ in range(3):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")
    with pytest.raises(HTTPException):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")
    clock["value"] += 60

    enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")


def test_identifiers_do_not_share_a_counter(db_session, clock):
    for _ in range(3):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")

    enforce_rate_limit(db_session, THREE_PER_MINUTE, "joao@example.com")


def test_identifier_is_case_and_space_insensitive(db_session, clock):
    for identifier in ["ANA@example.com", " ana@example.com ", "Ana@Example.com"]:
        enforce_rate_limit(db_session, THREE_PER_MINUTE, identifier)

    with pytest.raises(HTTPException):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")


def test_rule_names_do_not_share_a_counter(db_session, clock):
    other = (RateLimit("other", 3, 60),)
    for _ in range(3):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")

    enforce_rate_limit(db_session, other, "ana@example.com")


def test_every_rule_of_an_action_is_enforced(db_session, clock):
    rules = (RateLimit("mail", 1, 60), RateLimit("mail", 3, 3600))
    enforce_rate_limit(db_session, rules, "ana@example.com")

    with pytest.raises(HTTPException) as per_minute:
        enforce_rate_limit(db_session, rules, "ana@example.com")
    assert per_minute.value.headers["Retry-After"] == "60"

    clock["value"] += 61
    enforce_rate_limit(db_session, rules, "ana@example.com")

    clock["value"] += 61
    with pytest.raises(HTTPException) as per_hour:
        enforce_rate_limit(db_session, rules, "ana@example.com")
    assert int(per_hour.value.headers["Retry-After"]) > 60


def test_nothing_is_counted_when_rate_limiting_is_disabled(
    db_session, clock, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    for _ in range(10):
        enforce_rate_limit(db_session, THREE_PER_MINUTE, "ana@example.com")

    assert count_rows(db_session) == 0


def test_old_counters_are_purged(db_session, clock, monkeypatch):
    monkeypatch.setattr(rate_limit.random, "random", lambda: 0.0)
    enforce_rate_limit(db_session, THREE_PER_MINUTE, "old@example.com")
    clock["value"] += rate_limit.PURGE_AFTER_SECONDS + 1

    enforce_rate_limit(db_session, THREE_PER_MINUTE, "new@example.com")

    assert count_rows(db_session) == 1


def test_login_is_blocked_after_five_attempts(auth_client):
    payload = {"email": "ana@example.com", "password": "Wrong-Passw0rd!"}

    statuses = [auth_client.post(LOGIN_URL, json=payload).status_code for _ in range(6)]

    assert statuses == [401, 401, 401, 401, 401, 429]


def test_blocked_login_returns_retry_after(auth_client):
    payload = {"email": "ana@example.com", "password": "Wrong-Passw0rd!"}
    for _ in range(5):
        auth_client.post(LOGIN_URL, json=payload)

    response = auth_client.post(LOGIN_URL, json=payload)

    assert response.status_code == 429
    assert 0 < int(response.headers["retry-after"]) <= 60
    assert response.json() == {"detail": "Too many requests. Try again later."}


def test_known_and_unknown_emails_are_limited_the_same_way(auth_client, email_sender):
    register_and_verify(auth_client, email_sender, email="known@example.com")
    known = {"email": "known@example.com", "password": "Wrong-Passw0rd!"}
    unknown = {"email": "unknown@example.com", "password": "Wrong-Passw0rd!"}

    known_statuses = [
        auth_client.post(LOGIN_URL, json=known).status_code for _ in range(6)
    ]
    unknown_statuses = [
        auth_client.post(LOGIN_URL, json=unknown).status_code for _ in range(6)
    ]

    assert known_statuses == unknown_statuses == [401] * 5 + [429]


def test_login_limit_is_per_email(auth_client):
    for _ in range(6):
        auth_client.post(
            LOGIN_URL, json={"email": "ana@example.com", "password": "Wrong-Passw0rd!"}
        )

    response = auth_client.post(
        LOGIN_URL, json={"email": "joao@example.com", "password": "Wrong-Passw0rd!"}
    )

    assert response.status_code == 401


def test_a_blocked_login_is_not_checked_even_with_the_right_password(
    auth_client, email_sender
):
    register_and_verify(auth_client, email_sender)
    for _ in range(5):
        auth_client.post(
            LOGIN_URL, json={"email": "ana@example.com", "password": "Wrong-Passw0rd!"}
        )

    response = auth_client.post(
        LOGIN_URL, json={"email": "ana@example.com", "password": "Password123!"}
    )

    assert response.status_code == 429


def test_register_is_limited_per_ip(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE", 5)
    statuses = [
        auth_client.post(
            REGISTER_URL,
            json={
                "name": "Ana Silva",
                "email": f"ana{number}@example.com",
                "password": "Password123!",
            },
        ).status_code
        for number in range(6)
    ]

    assert statuses == [201, 201, 201, 201, 201, 429]


@pytest.mark.parametrize("url", [RESEND_URL, FORGOT_URL])
def test_email_endpoints_allow_one_request_per_minute(auth_client, clock, url):
    payload = {"email": "ana@example.com"}

    first = auth_client.post(url, json=payload)
    second = auth_client.post(url, json=payload)
    clock["value"] += 61
    third = auth_client.post(url, json=payload)

    assert (first.status_code, second.status_code, third.status_code) == (200, 429, 200)


@pytest.mark.parametrize("url", [RESEND_URL, FORGOT_URL])
def test_email_endpoints_allow_five_requests_per_hour(auth_client, clock, url):
    payload = {"email": "ana@example.com"}
    statuses = []
    for _ in range(6):
        statuses.append(auth_client.post(url, json=payload).status_code)
        clock["value"] += 61

    assert statuses == [200, 200, 200, 200, 200, 429]


def test_resend_and_forgot_password_have_separate_counters(auth_client, clock):
    payload = {"email": "ana@example.com"}

    assert auth_client.post(RESEND_URL, json=payload).status_code == 200
    assert auth_client.post(FORGOT_URL, json=payload).status_code == 200


def test_email_limit_does_not_reveal_whether_the_account_exists(
    auth_client, email_sender, clock
):
    register_and_verify(auth_client, email_sender, email="known@example.com")
    results = {}
    for email in ["known@example.com", "unknown@example.com"]:
        payload = {"email": email}
        results[email] = [
            auth_client.post(FORGOT_URL, json=payload).status_code for _ in range(2)
        ]

    assert results["known@example.com"] == results["unknown@example.com"] == [200, 429]


def as_ip(monkeypatch, address):
    monkeypatch.setattr("app.domains.auth.router.client_ip", lambda request: address)


def test_a_victim_is_not_locked_out_by_attempts_from_another_ip(
    auth_client, email_sender, monkeypatch
):
    register_and_verify(auth_client, email_sender)
    as_ip(monkeypatch, "203.0.113.50")
    attacker = [
        auth_client.post(
            LOGIN_URL, json={"email": "ana@example.com", "password": "Wrong-Passw0rd!"}
        ).status_code
        for _ in range(6)
    ]
    as_ip(monkeypatch, "198.51.100.7")

    victim = auth_client.post(
        LOGIN_URL, json={"email": "ana@example.com", "password": "Password123!"}
    )

    assert attacker == [401] * 5 + [429]
    assert victim.status_code == 200


def test_a_distributed_attack_on_one_email_is_capped(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_EMAIL_PER_MINUTE", 8)
    statuses = []
    for number in range(10):
        as_ip(monkeypatch, f"203.0.113.{number}")
        statuses.append(
            auth_client.post(
                LOGIN_URL,
                json={"email": "ana@example.com", "password": "Wrong-Passw0rd!"},
            ).status_code
        )

    assert statuses == [401] * 8 + [429, 429]


def test_one_ip_cannot_try_many_emails(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE", 6)
    as_ip(monkeypatch, "203.0.113.50")

    statuses = [
        auth_client.post(
            LOGIN_URL,
            json={"email": f"user{number}@example.com", "password": "Wrong-Passw0rd!"},
        ).status_code
        for number in range(8)
    ]

    assert statuses == [401] * 6 + [429, 429]


@pytest.mark.parametrize("url", [RESEND_URL, FORGOT_URL])
def test_email_endpoints_are_capped_per_ip(auth_client, monkeypatch, url):
    monkeypatch.setattr(settings, "RATE_LIMIT_EMAIL_PER_IP_PER_MINUTE", 4)
    as_ip(monkeypatch, "203.0.113.50")

    statuses = [
        auth_client.post(url, json={"email": f"user{number}@example.com"}).status_code
        for number in range(6)
    ]

    assert statuses == [200] * 4 + [429, 429]


def test_the_visitor_is_identified_by_the_address_of_the_connection():
    known = Request({"type": "http", "client": ("203.0.113.5", 5000), "headers": []})
    unknown = Request({"type": "http", "client": None, "headers": []})

    assert client_ip(known) == "203.0.113.5"
    assert client_ip(unknown) == "unknown"


def test_two_visitors_do_not_share_a_limit(auth_client):
    payload = {"email": "ana@example.com", "password": "Wrong-Passw0rd!"}
    first = TestClient(app, base_url="https://testserver", client=("203.0.113.1", 1000))
    second = TestClient(
        app, base_url="https://testserver", client=("203.0.113.2", 1000)
    )

    first_statuses = [first.post(LOGIN_URL, json=payload).status_code for _ in range(6)]
    second_status = second.post(LOGIN_URL, json=payload).status_code

    assert first_statuses == [401, 401, 401, 401, 401, 429]
    assert second_status == 401


APPROVED_DEFAULTS = {
    "RATE_LIMIT_ENABLED": True,
    "RATE_LIMIT_LOGIN_PER_MINUTE": 5,
    "RATE_LIMIT_LOGIN_PER_EMAIL_PER_MINUTE": 20,
    "RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE": 30,
    "RATE_LIMIT_REGISTER_PER_MINUTE": 2,
    "RATE_LIMIT_EMAIL_PER_MINUTE": 1,
    "RATE_LIMIT_EMAIL_PER_HOUR": 5,
    "RATE_LIMIT_EMAIL_PER_IP_PER_MINUTE": 10,
    "RATE_LIMIT_PASSWORD_CHANGE_PER_15_MINUTES": 2,
    "RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE": 20,
}


def test_the_default_limits_are_the_approved_ones():
    defaults = {name: Settings.model_fields[name].default for name in APPROVED_DEFAULTS}

    assert defaults == APPROVED_DEFAULTS


def test_registration_allows_two_a_minute_per_ip(auth_client, clock):
    def register(number):
        return auth_client.post(
            REGISTER_URL,
            json={
                "name": "Ana Silva",
                "email": f"ana{number}@example.com",
                "password": "Password123!",
            },
        ).status_code

    first_two = [register(1), register(2)]
    third = register(3)
    clock["value"] += 59
    still_blocked = register(4)
    clock["value"] += 2
    after_the_window = register(5)

    assert first_two == [201, 201]
    assert (third, still_blocked, after_the_window) == (429, 429, 201)


def test_password_change_allows_two_attempts_every_fifteen_minutes(
    auth_client, email_sender, clock
):
    register_and_verify(auth_client, email_sender)
    auth_client.post(
        LOGIN_URL, json={"email": "ana@example.com", "password": "Password123!"}
    )
    guess = {"current_password": "Wrong-Passw0rd!", "new_password": "NewPassword123!"}

    def attempt():
        return auth_client.put(CHANGE_PASSWORD_URL, json=guess).status_code

    first_three = [attempt(), attempt(), attempt()]
    clock["value"] += 899
    inside_the_window = attempt()
    clock["value"] += 2
    after_the_window = attempt()

    assert first_three == [401, 401, 429]
    assert (inside_the_window, after_the_window) == (429, 401)
