from app.domains.users.make_admin import promote_to_admin
from app.domains.users.models import Role
from app.domains.users.schemas import UserRegister
from app.domains.users.service import create_user, mark_user_verified


def test_promote_user_not_found(db_session, capsys):
    code = promote_to_admin(db_session, "nonexistent@example.com")
    out, _ = capsys.readouterr()
    assert code == 1
    assert "not found" in out


def test_promote_unverified_user_fails(db_session, capsys):
    user = create_user(
        db_session,
        UserRegister(
            name="Unverified User",
            email="unverified@example.com",
            password="Password1!",
            accept_terms=True,
        ),
    )
    code = promote_to_admin(db_session, user.email)
    out, _ = capsys.readouterr()
    assert code == 1
    assert "is not verified" in out
    assert user.role == Role.USER


def test_promote_verified_user_to_admin(db_session, capsys):
    user = create_user(
        db_session,
        UserRegister(
            name="Teste Válido",
            email="verificado@example.com",
            password="Password1!",
            accept_terms=True,
        ),
    )
    mark_user_verified(db_session, user)
    code = promote_to_admin(db_session, user.email)
    out, _ = capsys.readouterr()
    assert code == 0
    assert "promoted to admin" in out
    assert user.role == Role.ADMIN


def test_promote_user_already_admin(db_session, capsys):
    user = create_user(
        db_session,
        UserRegister(
            name="Admin Existente",
            email="admin@example.com",
            password="Password1!",
            accept_terms=True,
        ),
    )
    mark_user_verified(db_session, user)
    user.role = Role.ADMIN
    db_session.commit()

    code = promote_to_admin(db_session, user.email)
    out, _ = capsys.readouterr()
    assert code == 0
    assert "already an admin" in out
