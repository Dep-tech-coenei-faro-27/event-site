from datetime import timedelta

from fastapi import status

from app.core.security import ACCESS_COOKIE_NAME, create_access_token
from app.domains.users.schemas import UserRegister
from app.domains.users.service import create_user, mark_user_verified


def test_update_user_profile_reflected_in_get(client, db_session):
    user = create_user(
        db_session,
        UserRegister(
            name="Nome Antigo",
            email="update.profile@example.com",
            password="Password1!",
            accept_terms=True,
        ),
    )
    mark_user_verified(db_session, user)

    token = create_access_token(user.id, user.token_version, timedelta(minutes=15))
    client.cookies.set(ACCESS_COOKIE_NAME, token)

    put_response = client.put("/api/users/me", json={"name": "Nome Atualizado"})
    assert put_response.status_code == status.HTTP_200_OK
    assert put_response.json()["name"] == "Nome Atualizado"

    get_response = client.get("/api/users/me")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["name"] == "Nome Atualizado"
    assert get_response.json()["email"] == "update.profile@example.com"
