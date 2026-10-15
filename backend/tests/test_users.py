from fastapi import status

from app.domains.users.enums import Course, PortugueseInstitution
from tests.helpers import (
    LOGIN_URL,
    register_and_verify,
)

USERS_ME_URL = "/api/users/me"


def test_update_user_institution_and_course(auth_client, email_sender):
    register_and_verify(auth_client, email_sender, email="update_test@example.com")
    auth_client.post(
        LOGIN_URL, json={"email": "update_test@example.com", "password": "Password123!"}
    )

    update_payload = {
        "name": "Léo Editado",
        "institution": PortugueseInstitution.UPORTO.value,
        "course": Course.GESTAO.value,
    }

    response = auth_client.put(USERS_ME_URL, json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Léo Editado"
    assert data["institution"] == PortugueseInstitution.UPORTO.value
    assert data["course"] == Course.GESTAO.value


def test_update_user_with_invalid_course_fails(auth_client, email_sender):
    register_and_verify(auth_client, email_sender, email="invalid_course@example.com")
    auth_client.post(
        LOGIN_URL,
        json={"email": "invalid_course@example.com", "password": "Password123!"},
    )

    update_payload = {"name": "Léo Editado", "course": "Medicina Quântica"}

    response = auth_client.put(USERS_ME_URL, json=update_payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", "course"] for error in errors)
