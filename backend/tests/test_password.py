from tests.helpers import LOGIN_URL, extract_verification_token, register_and_verify
from tests.test_auth import FORGOT_PASSWORD_URL

CHANGE_PASSWORD_URL = "/api/auth/password"
RESET_PASSWORD_URL = "/api/auth/reset-password"


def test_change_password_success(auth_client, email_sender):
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
    assert response.json() == {"message": "Password changed successfully"}


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


def test_change_password_to_same_password(auth_client, email_sender):

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


def test_change_password_invalid_new_password(auth_client, email_sender):
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
    error = response.json()["detail"][0]
    assert error["type"] == "password_invalid"
    assert error["ctx"]["rules"] == ["missing_uppercase"]


def test_change_password_unauthenticated(client):
    response = client.put(
        CHANGE_PASSWORD_URL,
        json={
            "current_password": "Password123!",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"] == "Not authenticated. Missing access token cookie."
    )


def test_password_reset(auth_client, email_sender):
    register_and_verify(
        auth_client,
        email_sender,
        email="resettest@example.com",
        password="Password1789!",
    )

    email_sender.sent.clear()

    response = auth_client.post(
        FORGOT_PASSWORD_URL, json={"email": "resettest@example.com"}
    )

    assert response.status_code == 200
    assert len(email_sender.sent) == 1

    # extract_verification_token also works to extract the password reset token.
    reset_token = extract_verification_token(email_sender)

    response = auth_client.post(
        RESET_PASSWORD_URL,
        json={
            "token": reset_token,
            "new_password": "NewPassword1789!",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successfully"

    response = auth_client.post(
        RESET_PASSWORD_URL,
        json={
            "token": reset_token,
            "new_password": "AnotherNewPassword1789!",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Password reset token has already been used"

    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "resettest@example.com",
            "password": "NewPassword1789!",
        },
    )

    # user is able to log with new password after reset
    assert response.status_code == 200
    assert response.json() == {"message": "Login successful"}
