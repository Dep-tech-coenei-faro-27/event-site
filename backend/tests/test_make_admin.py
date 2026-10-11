from app.domains.users.make_admin import promote_to_admin
from app.domains.users.models import Role
from app.domains.users.schemas import UserRegister
from app.domains.users.service import create_user, mark_user_verified


def test_promote_user_not_found(db, capsys):
    code = promote_to_admin(db, "nonexistent@example.com")
    out, _ = capsys.readouterr()
    assert code == 1
    assert "User not found" in out


def test_promote_user_already_admin(db, capsys):
    user = create_user(db, UserRegister(
        name="Admin Existente",
        email="admin@example.com",
        password="Password1!",
        accept_terms=True
    ))
    mark_user_verified(db, user)
    user.role = Role.ADMIN
    db.commit()

    code = promote_to_admin(db, user.email)
    out, _ = capsys.readouterr()
    assert code == 0
    assert "User is already an admin" in out
