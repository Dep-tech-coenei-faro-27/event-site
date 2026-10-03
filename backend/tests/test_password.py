from tests.helpers import LOGIN_URL, register_and_verify

CHANGE_PASSWORD_URL = "/api/auth/password"

def test_change_password_success(auth_client,email_sender):
    register_and_verify(
        auth_client,
        email_sender,
        email="john-doe@example.com",
        password="Password123!",
    )

    login_response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "john-doe@example.com",
            "password": "Password123!",
        },
    )

    assert login_response.status_code == 200

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={
            "current_password": "Password123!",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password changed successfully"
    }


def test_change_password_wrong_current_password(auth_client, email_sender):
    register_and_verify(
        auth_client,
        email_sender,
        email="jane-doe@example.com",
        password="Password567!",
    )

    login_response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "jane-doe@example.com",
            "password": "Password567!",
        },
    )

    assert login_response.status_code == 200

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword567!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Current password is incorrect"


def test_change_password_to_same_password(auth_client,email_sender):
    
    register_and_verify(
        auth_client,
        email_sender,
        email="password-test@example.com",
        password="Password123!",
    )

    login_response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "password-test@example.com",
            "password": "Password123!",
        },
    )

    assert login_response.status_code == 200

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={
            "current_password": "Password123!",
            "new_password": "Password123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Your new password must be different from your current password"
    )

def test_change_password_invalid_new_password(auth_client,email_sender):
    register_and_verify(
        auth_client,
        email_sender,
        email="john-doe@example.com",
        password="Password333_!",
    )

    login_response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "john-doe@example.com",
            "password": "Password333_!",
        },
    )

    assert login_response.status_code == 200

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={
            "current_password": "Password333_!",
            "new_password": "nouppercase123!",
        },
    )

    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"][0]["msg"]

def test_change_password_unauthenticated(client):
    response = client.put(
        CHANGE_PASSWORD_URL,
        json={
            "current_password": "Password123!",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated. Missing access token cookie."
