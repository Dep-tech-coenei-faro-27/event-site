import re

from fastapi import status
from sqlalchemy import select

from app.domains.auth.dependencies import ADMIN_REQUIRED_MESSAGE
from app.domains.users.enums import Role
from app.domains.users.models import User
from app.main import app
from tests.helpers import LOGIN_URL, register_and_verify

ADMIN_ME_URL = "/api/admin/me"
PASSWORD = "Password123!"


def _admin_routes():
    """Every (method, path) under /api/admin, read from the generated OpenAPI schema
    so it does not depend on how FastAPI stores included routers."""
    paths = app.openapi()["paths"]
    return [
        (method.upper(), re.sub(r"\{[^}]+\}", "1", path))
        for path, operations in sorted(paths.items())
        if path.startswith("/api/admin")
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    ]


def _login(auth_client, email):
    response = auth_client.post(LOGIN_URL, json={"email": email, "password": PASSWORD})
    assert response.status_code == status.HTTP_200_OK


def _set_role(db_session, email, role):
    user = db_session.scalar(select(User).where(User.email == email))
    user.role = role
    db_session.commit()


def test_admin_route_requires_a_session(auth_client):
    response = auth_client.get(ADMIN_ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_a_normal_user_gets_403_on_admin_routes(auth_client, email_sender):
    register_and_verify(auth_client, email_sender, email="normal@example.com")
    _login(auth_client, "normal@example.com")

    response = auth_client.get(ADMIN_ME_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == ADMIN_REQUIRED_MESSAGE


def test_an_admin_can_read_the_admin_profile(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender, email="chefe@example.com")
    _set_role(db_session, "chefe@example.com", Role.ADMIN)
    _login(auth_client, "chefe@example.com")

    response = auth_client.get(ADMIN_ME_URL)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == "chefe@example.com"
    assert body["role"] == "admin"
    assert "password_hash" not in body


def test_the_role_is_read_from_the_database_on_every_request(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender, email="mudou@example.com")
    _set_role(db_session, "mudou@example.com", Role.ADMIN)
    _login(auth_client, "mudou@example.com")
    assert auth_client.get(ADMIN_ME_URL).status_code == status.HTTP_200_OK

    # Demoted without logging in again: the same cookie must stop working at once.
    _set_role(db_session, "mudou@example.com", Role.USER)

    assert auth_client.get(ADMIN_ME_URL).status_code == status.HTTP_403_FORBIDDEN

    # And promoted again, with the same cookie, it works again.
    _set_role(db_session, "mudou@example.com", Role.ADMIN)

    assert auth_client.get(ADMIN_ME_URL).status_code == status.HTTP_200_OK


def test_an_inactive_admin_is_refused(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender, email="inativo@example.com")
    _set_role(db_session, "inativo@example.com", Role.ADMIN)
    _login(auth_client, "inativo@example.com")
    user = db_session.scalar(select(User).where(User.email == "inativo@example.com"))
    user.is_active = False
    db_session.commit()

    assert auth_client.get(ADMIN_ME_URL).status_code == status.HTTP_401_UNAUTHORIZED


def test_every_admin_route_refuses_a_normal_user(auth_client, email_sender):
    """Walks the real route table, so a future ``/admin`` route that forgets the
    dependency fails here instead of reaching production."""
    admin_routes = _admin_routes()
    assert admin_routes, "no /api/admin route is registered"

    register_and_verify(auth_client, email_sender, email="visitante@example.com")
    _login(auth_client, "visitante@example.com")

    for method, path in admin_routes:
        # Path parameters are filled with a dummy value: the permission check runs
        # before any lookup, so the answer must still be 403.
        response = auth_client.request(method, path)
        assert response.status_code == status.HTTP_403_FORBIDDEN, (method, path)


def test_every_admin_route_refuses_an_anonymous_visitor(auth_client):
    admin_routes = _admin_routes()
    assert admin_routes

    for method, path in admin_routes:
        response = auth_client.request(method, path)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, (method, path)
