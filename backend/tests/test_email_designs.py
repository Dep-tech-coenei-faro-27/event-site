"""Garantias do desenho dos emails entregues em ``ui-ux/ticket-email``.

O HTML e o texto são ficheiros de desenho com marcadores ``[ASSIM]``; o backend
substitui-os ao enviar. Estes testes impedem que o desenho volte a depender de
coisas que os clientes de email não suportam e que os marcadores se desencontrem.
"""

import re
from pathlib import Path

import pytest

DESIGN_DIR = Path(__file__).resolve().parents[2] / "ui-ux" / "ticket-email"

EMAILS = {
    "enei-ticket-confirmation-email": {
        "ATTENDEE_NAME",
        "EVENT_DATES",
        "EVENT_LOCATION",
        "FIRST_NAME",
        "TICKET_REFERENCE",
        "TICKET_TYPE",
        "TICKET_URL",
    },
    "enei-verification-email": {
        "FIRST_NAME",
        "VERIFICATION_URL",
        "VERIFICATION_VALIDITY_MINUTES",
    },
    "enei-password-reset-email": {
        "FIRST_NAME",
        "PASSWORD_RESET_URL",
        "RESET_VALIDITY_MINUTES",
    },
    "enei-password-changed-email": {
        "FIRST_NAME",
        "PASSWORD_RESET_REQUEST_URL",
    },
}

MARKER = re.compile(r"\[([A-Z][A-Z_]+)\]")
GMAIL_CLIPS_AT = 102 * 1024

pytestmark = pytest.mark.skipif(
    not DESIGN_DIR.is_dir(), reason="ui-ux/ticket-email não existe neste checkout"
)


def read(name: str, ext: str) -> str:
    return (DESIGN_DIR / f"{name}.{ext}").read_text(encoding="utf-8")


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("name", EMAILS)
def test_html_stays_under_the_gmail_clipping_limit(name):
    assert len(read(name, "html").encode("utf-8")) < GMAIL_CLIPS_AT


@pytest.mark.parametrize("name", EMAILS)
def test_html_is_a_600px_table_layout_in_portuguese(name):
    html = read(name, "html")
    assert 'lang="pt-PT"' in html
    assert "<table" in html
    assert "max-width:600px" in html
    assert 'width="600"' in html
    assert "max-width:640px" not in html


@pytest.mark.parametrize("name", EMAILS)
def test_html_does_not_use_what_email_clients_drop(name):
    html = read(name, "html")
    assert "background-image" not in html
    assert "url(" not in html
    assert "rgba(" not in html
    assert "<script" not in html
    assert "<link" not in html
    assert "@import" not in html
    assert not re.search(r"display:\s*(flex|grid)", html)


@pytest.mark.parametrize("name", EMAILS)
def test_html_has_a_preheader_and_a_solid_fallback_background(name):
    html = read(name, "html")
    assert re.search(r"display:none;max-height:0;overflow:hidden", html)
    assert 'bgcolor="#030710"' in html


@pytest.mark.parametrize("name", EMAILS)
def test_html_text_is_never_smaller_than_11px(name):
    sizes = [int(size) for size in re.findall(r"font-size:(\d+)px", read(name, "html"))]
    # o preheader escondido usa 1px de propósito
    assert min(size for size in sizes if size > 1) >= 11


@pytest.mark.parametrize("name,markers", EMAILS.items())
def test_html_and_text_carry_the_same_markers(name, markers):
    html_markers = set(MARKER.findall(read(name, "html")))
    text_markers = set(MARKER.findall(read(name, "txt")))
    assert html_markers == markers
    assert text_markers == markers


@pytest.mark.parametrize("name", EMAILS)
def test_every_link_is_a_marker(name):
    hrefs = re.findall(r'href="([^"]*)"', read(name, "html"))
    assert hrefs
    for href in hrefs:
        assert MARKER.fullmatch(href), href


@pytest.mark.parametrize("name", EMAILS)
def test_text_version_is_plain_and_signed(name):
    text = read(name, "txt")
    assert "<" not in text and ">" not in text
    assert text.startswith("ENEI 2027")
    assert text.rstrip().endswith("1–4 abril 2027")


@pytest.mark.parametrize("name", EMAILS)
def test_no_image_is_loaded_from_outside_the_message(name):
    sources = re.findall(r'<img[^>]*\ssrc="([^"]*)"', read(name, "html"))
    assert all(src.startswith("cid:") for src in sources)


def test_ticket_qr_is_the_240px_cid_image_with_alt_text():
    html = read("enei-ticket-confirmation-email", "html")
    images = re.findall(r"<img[^>]*>", html)
    assert len(images) == 1
    image = images[0]
    assert 'src="cid:ticket-qr"' in image
    assert 'width="240"' in image and 'height="240"' in image
    assert re.search(r'alt="[^"]{10,}"', image)
    # fundo branco por trás: o QR lê-se mesmo que o cliente inverta as cores
    assert 'bgcolor="#ffffff"' in html


def test_qr_has_no_extra_white_margin_around_the_png():
    # o PNG do backend já traz a zona de silêncio da norma (QR_BORDER); mais
    # branco à volta só encolhe a parte que se lê
    html = read("enei-ticket-confirmation-email", "html")
    cell = re.search(r'<td style="([^"]*)"><img src="cid:ticket-qr"', html)
    assert cell and "padding:0;" in cell.group(1)


def test_the_cid_matches_the_one_the_backend_attaches():
    from app.core.email.templates import TICKET_QR_CID

    assert f"cid:{TICKET_QR_CID}" in read("enei-ticket-confirmation-email", "html")


def test_account_emails_do_not_promise_a_fixed_link_lifetime():
    for name in ("enei-verification-email", "enei-password-reset-email"):
        html = read(name, "html")
        assert not re.search(r"\b\d+\s*(minutos|horas)\b", html)


VALIDATED_COLORS = {
    "#ffffff", "#c9d3e3", "#9fb0c6", "#23caff", "#4ade80", "#030710",
    "#050d21", "#081126", "#0d1a34", "#1d3b63", "#2a5a85",
}  # fmt: skip


@pytest.mark.parametrize("name", EMAILS)
def test_every_color_comes_from_the_validated_palette(name):
    used = set(re.findall(r"#[0-9a-fA-F]{6}\b", read(name, "html").lower()))
    assert used <= VALIDATED_COLORS, used - VALIDATED_COLORS


@pytest.mark.parametrize(
    "foreground,background,minimum",
    [
        ("#ffffff", "#050d21", 4.5),  # título
        ("#c9d3e3", "#050d21", 4.5),  # texto
        ("#9fb0c6", "#050d21", 4.5),  # texto secundário
        ("#23caff", "#050d21", 4.5),  # ligações e etiquetas
        ("#9fb0c6", "#0d1a34", 4.5),  # etiquetas do bilhete
        ("#23caff", "#0d1a34", 4.5),  # referência
        ("#ffffff", "#0d1a34", 4.5),  # valores do bilhete
        ("#4ade80", "#081126", 4.5),  # estado «confirmado»
        ("#23caff", "#081126", 4.5),  # cabeçalho
        ("#9fb0c6", "#081126", 4.5),  # subtítulo do cabeçalho
        ("#030710", "#23caff", 4.5),  # botão
    ],
)
def test_palette_contrast(foreground, background, minimum):
    assert contrast(foreground, background) >= minimum
    html = "".join(read(name, "html") for name in EMAILS).lower()
    assert foreground in html and background in html
