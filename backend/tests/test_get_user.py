from tests.helpers import (
    LOGIN_URL,
    register_and_verify,
)

USERS_ME_URL = "/api/users/me"


def test_get_users_me(auth_client, email_sender):
    email = "ana@example.com"
    password = "Password123!"

    register_and_verify(
        auth_client,
        email_sender,
        name="Ana Silva",
        email=email,
        password=password,
    )

    response = auth_client.get(USERS_ME_URL)
    assert response.status_code == 401

    login_response = auth_client.post(
        LOGIN_URL,
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    response = auth_client.get(USERS_ME_URL)
    assert response.status_code == 200
