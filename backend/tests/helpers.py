import re

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
ME_URL = "/api/auth/me"
VERIFY_URL = "/api/auth/verify-email"

TOKEN_QUERY = re.compile(r"[?&]token=([A-Za-z0-9._\-]+)")


def register_user(
    auth_client,
    email_sender,
    *,
    name="Ana Silva",
    email="ana@example.com",
    password="Password123!",
):
    response = auth_client.post(
        REGISTER_URL,
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return response


def extract_verification_token(email_sender) -> str:
    assert email_sender.sent
    link = TOKEN_QUERY.search(email_sender.sent[-1]["html_body"])
    assert link is not None
    return link.group(1)


def register_and_verify(
    auth_client,
    email_sender,
    *,
    name="Ana Silva",
    email="ana@example.com",
    password="Password123!",
):
    register_user(auth_client, email_sender, name=name, email=email, password=password)
    token = extract_verification_token(email_sender)
    response = auth_client.post(VERIFY_URL, json={"token": token})
    assert response.status_code == 200
    return response
