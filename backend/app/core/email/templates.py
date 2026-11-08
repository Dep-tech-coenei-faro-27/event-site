# ruff: noqa: E501
import re
from html import escape
from pathlib import Path

import app.core.config as config

VERIFICATION_EMAIL_SUBJECT = "Confirma o teu email"
PASSWORD_RESET_SUBJECT = "Recuperação de Password"
PASSWORD_CHANGED_SUBJECT = "A tua password foi alterada"
TICKET_EMAIL_SUBJECT = "O teu bilhete para o ENEI 2027"
TICKET_QR_CID = "ticket-qr"
TICKET_PATH = "/perfil"
FORGOT_PASSWORD_PATH = "/conta/recuperar"
EVENT_DATES = "1–4 abril 2027"
EVENT_LOCATION = "Campus de Gambelas, Faro"
MARKER_PATTERN = re.compile(r"\[([A-Z][A-Z_]*)\]")
_TICKET_HTML = Path(__file__).with_name("ticket_email.html")
_TICKET_TEXT = Path(__file__).with_name("ticket_email.txt")
_VERIFICATION_HTML = Path(__file__).with_name("verification_email.html")
_VERIFICATION_TEXT = Path(__file__).with_name("verification_email.txt")
_PASSWORD_RESET_HTML = Path(__file__).with_name("password_reset_email.html")
_PASSWORD_RESET_TEXT = Path(__file__).with_name("password_reset_email.txt")
_PASSWORD_CHANGED_HTML = Path(__file__).with_name("password_changed_email.html")
_PASSWORD_CHANGED_TEXT = Path(__file__).with_name("password_changed_email.txt")


def render_template(template: str, values: dict[str, str], *, html: bool = True) -> str:
    """Fill the ``[MARKER]`` placeholders of a designed email in a single pass.

    HTML values are escaped. A marker without a value, or a value without a
    marker, raises: a renamed field must never reach a customer as ``[TICKET_URL]``.
    The values are not scanned again, so a name written as ``[X]`` stays as typed.
    """
    found = set(MARKER_PATTERN.findall(template))
    if found != set(values):
        raise ValueError(
            "template markers and values differ: "
            f"{sorted(found.symmetric_difference(values))}"
        )

    def fill(match: re.Match[str]) -> str:
        value = values[match.group(1)]
        return escape(value, quote=True) if html else value

    return MARKER_PATTERN.sub(fill, template)


def ticket_url() -> str:
    """The page of the account where the ticket shows, with or without a final /."""
    return f"{config.settings.FRONTEND_URL.rstrip('/')}{TICKET_PATH}"


def build_ticket_email(
    attendee_name: str, tier_name: str, reference: str
) -> tuple[str, str]:
    """The ticket email as ``(html, plain text)``, with the same data in both."""
    parts = attendee_name.split()
    values = {
        "FIRST_NAME": parts[0] if parts else attendee_name,
        "ATTENDEE_NAME": attendee_name,
        "TICKET_TYPE": tier_name,
        "TICKET_REFERENCE": reference,
        "EVENT_DATES": EVENT_DATES,
        "EVENT_LOCATION": EVENT_LOCATION,
        "TICKET_URL": ticket_url(),
    }
    html = render_template(_TICKET_HTML.read_text(encoding="utf-8"), values)
    text = render_template(_TICKET_TEXT.read_text(encoding="utf-8"), values, html=False)
    return html, text


def _first_name(name: str) -> str:
    parts = name.split()
    return parts[0] if parts else name


def _render_pair(
    html_file: Path, text_file: Path, values: dict[str, str]
) -> tuple[str, str]:
    html = render_template(html_file.read_text(encoding="utf-8"), values)
    text = render_template(text_file.read_text(encoding="utf-8"), values, html=False)
    return html, text


def build_verification_email(name: str, verify_url: str) -> tuple[str, str]:
    """The email-confirmation email as ``(html, plain text)``."""
    return _render_pair(
        _VERIFICATION_HTML,
        _VERIFICATION_TEXT,
        {
            "FIRST_NAME": _first_name(name),
            "VERIFICATION_URL": verify_url,
            "VERIFICATION_VALIDITY_MINUTES": str(
                config.settings.JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES
            ),
        },
    )


def build_password_reset_email(name: str, reset_url: str) -> tuple[str, str]:
    """The password-recovery email as ``(html, plain text)``."""
    return _render_pair(
        _PASSWORD_RESET_HTML,
        _PASSWORD_RESET_TEXT,
        {
            "FIRST_NAME": _first_name(name),
            "PASSWORD_RESET_URL": reset_url,
            "RESET_VALIDITY_MINUTES": str(
                config.settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            ),
        },
    )


def build_password_changed_email(name: str) -> tuple[str, str]:
    """The "your password was changed" email, with a link to ask for a reset."""
    request_url = f"{config.settings.FRONTEND_URL.rstrip('/')}{FORGOT_PASSWORD_PATH}"
    return _render_pair(
        _PASSWORD_CHANGED_HTML,
        _PASSWORD_CHANGED_TEXT,
        {"FIRST_NAME": _first_name(name), "PASSWORD_RESET_REQUEST_URL": request_url},
    )
