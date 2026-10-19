import io

import pytest
import zxingcpp
from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.qr import (
    QR_BORDER,
    QR_SCALE,
    InvalidQRPayloadError,
    generate_qr_payload,
    render_qr_png,
    verify_qr_payload,
)
from app.db.base import Base
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.tickets.service import (
    PaymentNotConfirmedError,
    confirm_ticket_payment_and_issue_qr,
    issue_qr_for_confirmed_ticket,
)
from app.domains.users.models import User


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with testing_session_local() as session:
        yield session


def test_two_generations_never_produce_same_string():
    """Requirement: Teste: duas gerações nunca produzem a mesma string."""
    ticket_id = 105
    generated_payloads = {generate_qr_payload(ticket_id) for _ in range(1000)}
    assert len(generated_payloads) == 1000


def test_qr_payload_contains_no_personal_data():
    """Requirement: O payload sem dados pessoais."""
    payload = generate_qr_payload(ticket_id=42)
    assert "@" not in payload
    assert " " not in payload
    # Verifica que apenas contém o prefixo, o ID numérico, nonce e assinatura
    parts = payload.split(".")
    assert len(parts) == 4
    assert parts[0] == "ENEI27"
    assert parts[1] == "42"
    # Comprimento compacto (~70-80 chars) adequado para impressão P&B
    assert len(payload) < 90
    assert payload.isascii()


def test_qr_generated_and_saved_only_after_payment_confirmation(db_session: Session):
    """Requirement: Gerar string única após confirmação do pagamento e guardar."""
    user = User(
        name="Aluno Teste",
        email="aluno@ualg.pt",
        password_hash="hashed_pw",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    ticket = Ticket(
        user_id=user.id,
        transaction_reference="IFTHEN-999111",
        payment_status=PaymentStatus.PENDING,
    )
    db_session.add(ticket)
    db_session.commit()

    # Tentar gerar QR antes do pagamento ser confirmado deve falhar
    with pytest.raises(PaymentNotConfirmedError):
        issue_qr_for_confirmed_ticket(db_session, ticket)

    assert ticket.qr_payload is None

    # Após confirmação do pagamento, gera e guarda o QR
    confirmed_ticket = confirm_ticket_payment_and_issue_qr(db_session, ticket.id)
    assert confirmed_ticket.payment_status == PaymentStatus.PAID
    assert confirmed_ticket.qr_payload is not None
    assert confirmed_ticket.paid_at is not None

    verified = verify_qr_payload(confirmed_ticket.qr_payload)
    assert verified.ticket_id == ticket.id


@pytest.mark.parametrize(
    "bad_qr_secret",
    [
        "",
        "   ",
        "too-short",
        "dev-only-qr-secret-replace-me-0123456789abcdef",
        "a" * 48,  # igual à JWT_SECRET_KEY
    ],
)
def test_prod_rejects_missing_weak_or_duplicate_qr_secret(bad_qr_secret: str):
    """Requirement: Chave de assinatura em Secret, fora do código e forte em prod."""
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="QR_SECRET_KEY"):
        Settings(
            _env_file=None,
            ENVIRONMENT="prod",
            DEBUG=False,
            POSTGRES_USER="u",
            POSTGRES_PASSWORD="strong-db-password",
            POSTGRES_DB="d",
            POSTGRES_HOST="h",
            POSTGRES_PORT=5432,
            SMTP_HOST="smtp.enei.pt",
            EMAIL_SENDER="noreply@enei.pt",
            FRONTEND_URL="https://enei.pt",
            CORS_ALLOW_ORIGINS=["https://enei.pt"],
            JWT_SECRET_KEY="a" * 48,
            QR_SECRET_KEY=bad_qr_secret,
        )


def test_qr_signature_verification_and_tamper_resistance():
    """Ensure signed payload can be verified and rejects any tampering."""
    payload = generate_qr_payload(ticket_id=7)
    verified = verify_qr_payload(payload)
    assert verified.ticket_id == 7

    prefix, ticket_id, nonce, signature = payload.split(".")

    # 1. Adulterar o ticket_id
    with pytest.raises(InvalidQRPayloadError):
        verify_qr_payload(f"{prefix}.8.{nonce}.{signature}")

    # 2. Adulterar o nonce
    tampered_nonce = nonce[:-1] + ("a" if nonce[-1] != "a" else "b")
    with pytest.raises(InvalidQRPayloadError):
        verify_qr_payload(f"{prefix}.{ticket_id}.{tampered_nonce}.{signature}")

    # 3. Adulterar o prefixo
    with pytest.raises(InvalidQRPayloadError):
        verify_qr_payload(f"ENEI26.{ticket_id}.{nonce}.{signature}")

    # 4. Adulterar a própria assinatura
    tampered_sig = signature[:-1] + ("a" if signature[-1] != "a" else "b")
    with pytest.raises(InvalidQRPayloadError):
        verify_qr_payload(f"{prefix}.{ticket_id}.{nonce}.{tampered_sig}")


def _decodes_to(image, payload: str) -> bool:
    return any(r.text == payload for r in zxingcpp.read_barcodes(image))


def _rendered_qr(payload: str):
    return Image.open(io.BytesIO(render_qr_png(payload))).convert("L")


def test_rendered_qr_is_pure_black_and_white_with_quiet_zone():
    """Requirement: QR legível impresso a preto e branco."""
    payload = generate_qr_payload(ticket_id=123456)
    image = _rendered_qr(payload)

    histogram = image.histogram()
    assert histogram[0] and histogram[255]
    assert sum(histogram[1:255]) == 0  # sem cinzentos
    # Zona de silêncio de 4 módulos em branco à volta do símbolo
    quiet = QR_BORDER * QR_SCALE
    width, height = image.size
    for box in (
        (0, 0, width, quiet),
        (0, height - quiet, width, height),
        (0, 0, quiet, height),
        (width - quiet, 0, width, height),
    ):
        assert image.crop(box).getextrema() == (255, 255)

    assert _decodes_to(image, payload)
    assert verify_qr_payload(payload).ticket_id == 123456


@pytest.mark.parametrize("size_px", [240, 160, 120])
def test_rendered_qr_survives_a_poor_print(size_px: int):
    """Impressão fraca: reduzido (até ~3 cm), desfocado e com toner cinzento."""
    payload = generate_qr_payload(ticket_id=123456)
    image = _rendered_qr(payload).resize((size_px, size_px), Image.BILINEAR)
    image = image.filter(ImageFilter.GaussianBlur(1.0))
    image = image.point(lambda v: int(255 - (255 - v) * 0.6))

    assert _decodes_to(image, payload)


def test_rendered_qr_survives_a_crease_over_the_centre():
    """Um vinco ou mancha branca no meio do bilhete não impede a leitura."""
    payload = generate_qr_payload(ticket_id=123456)
    image = _rendered_qr(payload)
    width = image.size[0]
    side = int(width * 0.3)
    centre = width // 2
    ImageDraw.Draw(image).rectangle(
        (
            centre - side // 2,
            centre - side // 2,
            centre + side // 2,
            centre + side // 2,
        ),
        fill=255,
    )

    assert _decodes_to(image, payload)
