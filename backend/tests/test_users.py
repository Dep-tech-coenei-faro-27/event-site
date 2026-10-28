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


def _login(auth_client, email_sender, email):
    register_and_verify(auth_client, email_sender, email=email)
    auth_client.post(LOGIN_URL, json={"email": email, "password": "Password123!"})


def test_a_new_account_has_no_phone(auth_client, email_sender):
    _login(auth_client, email_sender, "no_phone@example.com")

    response = auth_client.get(USERS_ME_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["phone"] is None


def test_update_user_phone_is_saved_normalized_and_returned(auth_client, email_sender):
    _login(auth_client, email_sender, "phone@example.com")

    response = auth_client.put(USERS_ME_URL, json={"phone": "+351 912-345.678"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["phone"] == "+351912345678"
    assert auth_client.get(USERS_ME_URL).json()["phone"] == "+351912345678"


def test_phone_00_prefix_becomes_plus(auth_client, email_sender):
    _login(auth_client, email_sender, "phone00@example.com")

    response = auth_client.put(USERS_ME_URL, json={"phone": "00351 912 345 678"})

    assert response.json()["phone"] == "+351912345678"


def test_updating_only_the_name_keeps_the_phone(auth_client, email_sender):
    _login(auth_client, email_sender, "keep_phone@example.com")
    auth_client.put(USERS_ME_URL, json={"phone": "912345678"})

    response = auth_client.put(USERS_ME_URL, json={"name": "Novo Nome"})

    assert response.json()["name"] == "Novo Nome"
    assert response.json()["phone"] == "912345678"


def test_null_or_empty_phone_removes_it(auth_client, email_sender):
    _login(auth_client, email_sender, "clear_phone@example.com")
    auth_client.put(USERS_ME_URL, json={"phone": "912345678"})

    assert auth_client.put(USERS_ME_URL, json={"phone": None}).json()["phone"] is None

    auth_client.put(USERS_ME_URL, json={"phone": "912345678"})
    assert auth_client.put(USERS_ME_URL, json={"phone": "  "}).json()["phone"] is None


def test_invalid_phone_is_rejected(auth_client, email_sender):
    _login(auth_client, email_sender, "bad_phone@example.com")

    for bad in ["12345", "abcdefghi", "+1234567890123456", "912 345 67x"]:
        response = auth_client.put(USERS_ME_URL, json={"phone": bad})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, bad
        errors = response.json()["detail"]
        assert any(error["loc"] == ["body", "phone"] for error in errors), bad

    assert auth_client.get(USERS_ME_URL).json()["phone"] is None
