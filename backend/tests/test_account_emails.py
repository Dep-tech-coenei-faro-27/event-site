"""The three account emails use the design in ``ui-ux/ticket-email``.

Verification, password recovery and "password changed" are rendered from the same
HTML and plain-text files as the ticket email, with the minutes of validity taken
from the settings, and are queued with both bodies.
"""

import re
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.email.templates import (
    FORGOT_PASSWORD_PATH,
    PASSWORD_CHANGED_SUBJECT,
    PASSWORD_RESET_SUBJECT,
    VERIFICATION_EMAIL_SUBJECT,
    build_password_changed_email,
    build_password_reset_email,
    build_verification_email,
)
from tests.helpers import register_and_verify

LINK = "https://ualg.eneiconf.pt/conta/verificar?token=abc.def&x=1"
MARKER = re.compile(r"\[[A-Z][A-Z_]+\]")
EMAIL_DIR = Path(__file__).resolve().parents[1] / "app" / "core" / "email"
DESIGN_DIR = Path(__file__).resolve().parents[2] / "ui-ux" / "ticket-email"

# (copy in the backend, file in the design folder)
COPIES = [
    ("ticket_email", "enei-ticket-confirmation-email"),
    ("verification_email", "enei-verification-email"),
    ("password_reset_email", "enei-password-reset-email"),
    ("password_changed_email", "enei-password-changed-email"),
]


@pytest.fixture(autouse=True)
def no_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def test_the_verification_email_has_both_bodies_and_no_marker_left():
    html, text = build_verification_email("Ana Silva", LINK)

    assert not MARKER.search(html)
    assert not MARKER.search(text)
    assert 'width="600"' in html
    assert "<" not in text
    assert "Olá Ana." in text


def test_the_links_carry_the_url_in_both_bodies():
    html, text = build_verification_email("Ana", LINK)

    assert "token=abc.def&amp;x=1" in html
    assert LINK in text


def test_the_minutes_of_validity_come_from_the_settings(monkeypatch):
    monkeypatch.setattr(settings, "JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES", 47)
    monkeypatch.setattr(settings, "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 11)

    verification_html, verification_text = build_verification_email("Ana", LINK)
    reset_html, reset_text = build_password_reset_email("Ana", LINK)

    assert "47 minutos" in verification_html
    assert "47 minutos" in verification_text
    assert "11 minutos" in reset_html
    assert "11 minutos" in reset_text
    assert "24 horas" not in verification_html + reset_html


def test_a_name_written_as_html_is_escaped_in_the_html_and_plain_in_the_text():
    html, text = build_verification_email("<script>alert(1)</script>", LINK)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "Olá <script>alert(1)</script>." in text


def test_only_the_first_name_is_used():
    html, _ = build_password_changed_email("Ana Maria Silva")

    assert ">Ana</strong>" in html
    assert "Maria" not in html


def test_the_password_changed_email_links_to_the_recovery_page(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://eneiconf.pt/")

    html, text = build_password_changed_email("Ana")

    assert "https://eneiconf.pt/conta/recuperar" in html
    assert "https://eneiconf.pt/conta/recuperar" in text
    assert FORGOT_PASSWORD_PATH == "/conta/recuperar"


def test_the_recovery_email_has_the_link_and_a_text_body():
    html, text = build_password_reset_email(
        "Ana", "https://x.pt/conta/redefinir?token=t"
    )

    assert "https://x.pt/conta/redefinir?token=t" in html
    assert "https://x.pt/conta/redefinir?token=t" in text
    assert "Recuperação" in html


def test_register_queues_the_designed_verification_email(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)

    first = email_sender.sent[0]
    assert first["subject"] == VERIFICATION_EMAIL_SUBJECT
    assert 'width="600"' in first["html_body"]
    assert first["text_body"]
    assert "conta/verificar?token=" in first["text_body"]
    assert "<" not in first["text_body"]


def test_forgot_password_queues_both_bodies(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    email_sender.sent.clear()

    auth_client.post("/api/auth/forgot-password", json={"email": "ana@example.com"})

    sent = email_sender.sent[0]
    assert sent["subject"] == PASSWORD_RESET_SUBJECT
    assert 'width="600"' in sent["html_body"]
    assert "conta/redefinir?token=" in sent["text_body"]


def test_changing_the_password_queues_both_bodies(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    auth_client.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": "Password123!"}
    )

    response = auth_client.put(
        "/api/auth/password",
        json={"current_password": "Password123!", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 200
    notice = email_sender.sent[-1]
    assert notice["subject"] == PASSWORD_CHANGED_SUBJECT
    assert 'width="600"' in notice["html_body"]
    assert "conta/recuperar" in notice["text_body"]


@pytest.mark.skipif(
    not DESIGN_DIR.is_dir(), reason="ui-ux/ticket-email não existe neste checkout"
)
@pytest.mark.parametrize(("copy", "design"), COPIES)
@pytest.mark.parametrize("extension", ["html", "txt"])
def test_the_backend_copy_is_the_design_file(copy, design, extension):
    """The backend carries a copy (the image has only ``backend/``): keep it equal."""
    assert (EMAIL_DIR / f"{copy}.{extension}").read_text(encoding="utf-8") == (
        DESIGN_DIR / f"{design}.{extension}"
    ).read_text(encoding="utf-8")
