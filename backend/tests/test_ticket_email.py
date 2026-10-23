"""The ticket email: its design, its two bodies, its link and the real message."""

import io
import re
import smtplib
from datetime import UTC, datetime, timedelta

import pytest
import zxingcpp
from PIL import Image, ImageFilter
from sqlalchemy.orm import Session

import app.core.config as config
from app.core.email.models import EmailStatus
from app.core.email.outbox import (
    delete_old_emails,
    deliver_due,
    enqueue_email,
)
from app.core.email.smtp import SmtpEmailSender
from app.core.email.templates import (
    MARKER_PATTERN,
    TICKET_QR_CID,
    build_ticket_email,
    render_template,
    ticket_url,
)
from app.core.qr import generate_qr_payload, render_qr_png
from tests.test_email_service import _make_server

HTML_LIMIT_BYTES = 102 * 1024
INJECTION = '"><script>alert(1)</script>'


@pytest.fixture(autouse=True)
def frontend(monkeypatch):
    monkeypatch.setattr(config.settings, "FRONTEND_URL", "https://enei.pt")


def test_the_renderer_escapes_every_value_in_html():
    html = render_template("<p>[NAME]</p>", {"NAME": INJECTION})

    assert "<script>" not in html
    assert "&quot;&gt;&lt;script&gt;" in html


def test_the_renderer_keeps_plain_text_as_typed():
    text = render_template("Olá [NAME]", {"NAME": "Ana & Rui"}, html=False)

    assert text == "Olá Ana & Rui"


@pytest.mark.parametrize(
    "values",
    [{}, {"NAME": "Ana", "EXTRA": "x"}],
    ids=["missing value", "value without marker"],
)
def test_the_renderer_fails_when_markers_and_values_differ(values):
    with pytest.raises(ValueError, match="differ"):
        render_template("[NAME] [OTHER]" if not values else "[NAME]", values)


def test_a_value_that_looks_like_a_marker_is_not_replaced_again():
    html = render_template("[A] [B]", {"A": "[B]", "B": "x"})

    assert html == "[B] x"


def test_the_ticket_email_leaves_no_marker_in_either_body():
    html, text = build_ticket_email("Ana Silva", "Passe geral", "ENEI-ABC")

    assert not MARKER_PATTERN.search(html)
    assert not MARKER_PATTERN.search(text)


def test_both_bodies_carry_the_same_data():
    html, text = build_ticket_email("Ana Silva", "Passe geral", "ENEI-ABC")

    for value in ("Ana Silva", "Passe geral", "ENEI-ABC", "Faro", "abril 2027"):
        assert value in html
        assert value in text
    assert "<" not in text
    assert "https://enei.pt/perfil" in html
    assert "https://enei.pt/perfil" in text


def test_the_greeting_uses_the_first_name_only():
    html, text = build_ticket_email("Ana Maria Silva", "Passe geral", "R")

    assert "Olá, Ana." in text
    assert re.search(r"Olá\s*<strong[^>]*>Ana</strong>\.", html)


def test_the_name_is_escaped_in_the_html_and_not_in_the_text():
    html, text = build_ticket_email(INJECTION, "Passe geral", "R")

    assert "<script>" not in html
    assert INJECTION in text


@pytest.mark.parametrize("url", ["https://enei.pt", "https://enei.pt/"])
def test_the_link_goes_to_the_profile_with_or_without_a_final_slash(monkeypatch, url):
    monkeypatch.setattr(config.settings, "FRONTEND_URL", url)

    assert ticket_url() == "https://enei.pt/perfil"
    html, _ = build_ticket_email("Ana", "Passe geral", "R")
    assert 'href="https://enei.pt/perfil"' in html


def test_the_html_stays_under_the_size_gmail_clips_at():
    html, _ = build_ticket_email("Ana", "Passe geral", "R")

    assert len(html.encode()) < HTML_LIMIT_BYTES


def test_the_html_has_no_external_or_data_images():
    html, _ = build_ticket_email("Ana", "Passe geral", "R")

    assert re.findall(r'<img[^>]*src="([^"]+)"', html) == [f"cid:{TICKET_QR_CID}"]
    assert "url(" not in html


def _send_ticket_email(monkeypatch, payload):
    """The message the SMTP sender builds for a ticket, as the server receives it."""
    servers = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", _make_server(servers))
    html, text = build_ticket_email("Ana Silva", "Passe geral", "ENEI-ABC")
    SmtpEmailSender(
        host="smtp.example.com",
        port=465,
        username="",
        password="",
        from_email="no-reply@example.com",
    ).send_html(
        "ana@example.com",
        "Bilhete",
        html,
        {TICKET_QR_CID: render_qr_png(payload)},
        text_body=text,
    )
    return servers[0].sent_message, html, text


def test_the_real_message_is_alternative_text_then_related_html_and_png(monkeypatch):
    payload = generate_qr_payload(7)

    message, _, text = _send_ticket_email(monkeypatch, payload)

    assert message.get_content_type() == "multipart/alternative"
    plain, related = list(message.iter_parts())
    assert plain.get_content_type() == "text/plain"
    assert plain.get_content() == text
    assert related.get_content_type() == "multipart/related"
    html_part, image = list(related.iter_parts())
    assert html_part.get_content_type() == "text/html"
    cid = image["Content-ID"].strip("<>")
    assert f"cid:{cid}" in html_part.get_content()
    decoded = zxingcpp.read_barcodes(Image.open(io.BytesIO(image.get_content())))
    assert [barcode.text for barcode in decoded] == [payload]
    assert not MARKER_PATTERN.search(html_part.get_content())
    assert not MARKER_PATTERN.search(plain.get_content())


@pytest.mark.parametrize("size_px", [240, 120])
def test_the_png_in_the_email_decodes_small_and_blurred(monkeypatch, size_px):
    """The picture that reaches the inbox, shrunk and blurred like a poor print."""
    payload = generate_qr_payload(7)
    message, _, _ = _send_ticket_email(monkeypatch, payload)
    _, related = list(message.iter_parts())
    image = list(related.iter_parts())[1]
    picture = Image.open(io.BytesIO(image.get_content())).convert("L")
    picture = picture.resize((size_px, size_px), Image.BILINEAR)
    picture = picture.filter(ImageFilter.GaussianBlur(1.0))

    decoded = zxingcpp.read_barcodes(picture)

    assert [barcode.text for barcode in decoded] == [payload]


class Recorder:
    def __init__(self):
        self.calls = []

    def send_html(self, to_email, subject, html_body, **extras):
        self.calls.append(extras)


def test_the_text_body_reaches_the_transport_and_is_emptied_once_sent(
    test_engine,
):
    with Session(bind=test_engine) as db:
        row = enqueue_email(
            db, "a@example.com", "x", "<p>x</p>", text_body="x", dedupe_key="t:1"
        )
        transport = Recorder()

        deliver_due(db, transport)

        assert transport.calls == [{"text_body": "x"}]
        db.refresh(row)
        assert row.status == EmailStatus.SENT
        assert row.text_body is None
        assert row.html_body == ""
        assert not row.inline_images
        db.delete(row)
        db.commit()


def test_a_failed_row_is_cleaned_of_text_and_images(test_engine):
    with Session(bind=test_engine) as db:
        row = enqueue_email(
            db,
            "a@example.com",
            "x",
            "<p>x</p>",
            text_body="x",
            inline_images={"qr": b"\x89PNG"},
            dedupe_key="t:2",
        )
        row.status = EmailStatus.FAILED
        row.created_at = datetime.now(UTC) - timedelta(days=2)
        db.commit()

        delete_old_emails(db)

        db.refresh(row)
        assert row.text_body is None
        assert row.html_body == ""
        assert not row.inline_images
        db.delete(row)
        db.commit()


def test_the_stacked_columns_on_a_phone_do_not_overflow_the_ticket():
    """Full-width cells with padding need border-box or they stick out of the card."""
    html, _ = build_ticket_email("Ana", "Passe geral", "R")

    rule = re.search(r"\.ticket-column, \.qr-column \{([^}]*)\}", html)
    assert rule is not None
    assert "width: 100%" in rule.group(1)
    assert "box-sizing: border-box" in rule.group(1)
