import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.domains.users.models import Role, User


def add_user(db_session, email="ana@example.com"):
    user = User(name="Ana Silva", email=email, password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_new_users_get_safe_defaults(db_session):
    user = add_user(db_session)

    assert user.role == Role.USER
    assert user.is_active is True
    assert user.is_verified is False
    assert user.token_version == 0
    assert user.created_at is not None
    assert user.updated_at is not None


def test_emails_are_unique_regardless_of_case(db_session):
    add_user(db_session, "ana@example.com")

    with pytest.raises(IntegrityError):
        add_user(db_session, "ANA@Example.com")


def test_role_defaults_in_the_database_when_omitted(db_session):
    role = db_session.execute(
        text(
            "INSERT INTO users (name, email, password_hash) "
            "VALUES ('Ana', 'ana@example.com', 'hash') RETURNING role"
        )
    ).scalar()

    assert role == "USER"


def test_role_rejects_unknown_values(db_session):
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Ana', 'ana@example.com', 'hash', 'SUPERADMIN')"
            )
        )


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "   "},
        {"name": ""},
        {"email": "  "},
        {"password_hash": ""},
    ],
)
def test_the_database_refuses_blank_name_email_or_hash(db_session, fields):
    values = {"name": "Ana Silva", "email": "ana@example.com", "password_hash": "hash"}
    db_session.add(User(**{**values, **fields}))

    with pytest.raises(IntegrityError):
        db_session.commit()
