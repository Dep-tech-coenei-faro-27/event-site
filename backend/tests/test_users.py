from fastapi import status

from tests.helpers import (
    LOGIN_URL,
    register_and_verify,
)

USERS_ME_URL = "/api/users/me"


def test_update_user_name_ignores_institution_and_course(auth_client, email_sender):
    register_and_verify(auth_client, email_sender, email="update_test@example.com")
    auth_client.post(
        LOGIN_URL, json={"email": "update_test@example.com", "password": "Password123!"}
    )

    update_payload = {
        "name": "Léo Editado",
        "institution": "Universidade Inventada de Hogwarts",
        "course": "Medicina Quântica",
    }

    response = auth_client.put(USERS_ME_URL, json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Léo Editado"
    assert "institution" not in data
    assert "course" not in data
