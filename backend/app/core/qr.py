import base64
import hashlib
import hmac
import io
import secrets
from dataclasses import dataclass

import segno

import app.core.config as config

QR_PREFIX = "ENEI27"
NONCE_BYTES = 12


class InvalidQRPayloadError(ValueError):
    """Raised when the QR payload is malformed or has an invalid signature."""


@dataclass(frozen=True)
class VerifiedQRPayload:
    ticket_id: int
    nonce: str
    raw_payload: str


def _sign_data(data: str) -> str:
    secret = config.settings.QR_SECRET_KEY.encode("utf-8")
    digest = hmac.new(secret, data.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_qr_payload(ticket_id: int) -> str:
    """Generate a unique, HMAC-signed, PII-free QR payload for a ticket.

    Format: ``ENEI27.<ticket_id>.<nonce>.<signature>``
    Uses URL-safe characters without padding to keep the QR code compact
    and easily readable when printed in black and white.
    """
    if ticket_id <= 0:
        raise ValueError("Ticket ID must be a positive integer")

    nonce = secrets.token_urlsafe(NONCE_BYTES)
    unsigned_part = f"{QR_PREFIX}.{ticket_id}.{nonce}"
    signature = _sign_data(unsigned_part)
    return f"{unsigned_part}.{signature}"


def verify_qr_payload(payload: str) -> VerifiedQRPayload:
    """Verify the cryptographic signature and structure of a QR payload."""
    parts = payload.strip().split(".")
    if len(parts) != 4:
        raise InvalidQRPayloadError("Invalid QR payload format")

    prefix, ticket_id_str, nonce, signature = parts
    if prefix != QR_PREFIX or not nonce or not signature:
        raise InvalidQRPayloadError("Invalid QR payload prefix")

    if not ticket_id_str.isdigit():
        raise InvalidQRPayloadError("Ticket ID must be numeric")

    ticket_id = int(ticket_id_str)
    if ticket_id <= 0:
        raise InvalidQRPayloadError("Ticket ID must be a positive integer")

    unsigned_part = f"{QR_PREFIX}.{ticket_id}.{nonce}"
    expected_signature = _sign_data(unsigned_part)

    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidQRPayloadError("Invalid QR payload signature")

    return VerifiedQRPayload(
        ticket_id=ticket_id,
        nonce=nonce,
        raw_payload=payload.strip(),
    )


def render_qr_png(payload: str) -> bytes:
    """Render a QR payload as a black and white PNG for the ticket email."""
    buffer = io.BytesIO()
    segno.make(payload, error="m").save(buffer, kind="png", scale=8, border=4)
    return buffer.getvalue()
