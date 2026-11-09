from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.domains.users.cleanup import delete_unverified_users
from app.domains.users.models import User


def add_user(db_session, email, *, verified=False, age_days=0):
    user = User(
        name="Ana Silva",
        email=email,
        password_hash="hash",
        is_verified=verified,
    )
    db_session.add(user)
    db_session.commit()
    db_session.execute(
        update(User)
        .where(User.email == email)
        .values(created_at=datetime.now(UTC) - timedelta(days=age_days))
    )
    db_session.commit()


def remaining_emails(db_session):
    return set(db_session.scalars(select(User.email)))


def test_old_unverified_accounts_are_deleted(db_session):
    add_user(db_session, "old@example.com", age_days=10)

    deleted = delete_unverified_users(db_session, 7)

    assert deleted == 1
    assert remaining_emails(db_session) == set()


def test_recent_unverified_accounts_are_kept(db_session):
    add_user(db_session, "recent@example.com", age_days=2)

    assert delete_unverified_users(db_session, 7) == 0
    assert remaining_emails(db_session) == {"recent@example.com"}


def test_verified_accounts_are_never_deleted(db_session):
    add_user(db_session, "verified@example.com", verified=True, age_days=365)

    assert delete_unverified_users(db_session, 7) == 0
    assert remaining_emails(db_session) == {"verified@example.com"}


def test_only_the_old_unverified_accounts_are_deleted(db_session):
    add_user(db_session, "old@example.com", age_days=30)
    add_user(db_session, "recent@example.com", age_days=1)
    add_user(db_session, "verified@example.com", verified=True, age_days=30)

    deleted = delete_unverified_users(db_session, 7)

    assert deleted == 1
    assert remaining_emails(db_session) == {
        "recent@example.com",
        "verified@example.com",
    }


def test_deleting_frees_the_email_for_a_new_registration(auth_client, db_session):
    add_user(db_session, "squatted@example.com", age_days=10)
    delete_unverified_users(db_session, 7)

    response = auth_client.post(
        "/api/auth/register",
        json={
            "name": "Ana Silva",
            "email": "squatted@example.com",
            "password": "Password123!",
            "accept_terms": True,
        },
    )

    assert response.status_code == 201
