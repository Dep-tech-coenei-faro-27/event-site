from datetime import timedelta

from fastapi import status

from app.core.security import ACCESS_COOKIE_NAME, create_access_token
from app.domains.users.schemas import UserRegister
from app.domains.users.service import create_user, mark_user_verified


def test_update_user_profile_reflected_in_get(auth_client, db_session):
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
    auth_client.cookies.set(ACCESS_COOKIE_NAME, token)

    payload = {
        "name": "Nome Atualizado",
        "institution": "Universidade do Algarve",
        "course": "Engenharia Informática",
    }
    put_response = auth_client.put("/api/users/me", json=payload)
    assert put_response.status_code == status.HTTP_200_OK
    data = put_response.json()
    assert data["name"] == "Nome Atualizado"
    assert data["institution"] == "Universidade do Algarve"
    assert data["course"] == "Engenharia Informática"

    get_response = auth_client.get("/api/users/me")
    assert get_response.status_code == status.HTTP_200_OK
    get_data = get_response.json()
    assert get_data["name"] == "Nome Atualizado"
    assert get_data["institution"] == "Universidade do Algarve"
    assert get_data["course"] == "Engenharia Informática"
    assert get_data["email"] == "update.profile@example.com"
