"""Synthetic proofs of enrolment: PDFs signed by a test authority.

No real institution, student or seal is involved, so no personal data is in the
repository. The test authority takes the place of the EU trusted list.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO

from asn1crypto import core
from asn1crypto import keys as asn1_keys
from asn1crypto import x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID, ObjectIdentifier
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore

QC_STATEMENTS = ObjectIdentifier("1.3.6.1.5.5.7.1.3")
ORGANIZATION_IDENTIFIER = NameOID.ORGANIZATION_IDENTIFIER


@dataclass
class TestAuthority:
    key: ec.EllipticCurvePrivateKey
    cert: x509.Certificate

    @property
    def pem(self) -> bytes:
        return self.cert.public_bytes(serialization.Encoding.PEM)


def _name(common_name: str, **extra) -> x509.Name:
    attributes = [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    if extra.get("organization"):
        attributes.append(
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, extra["organization"])
        )
    if extra.get("identifier"):
        attributes.append(
            x509.NameAttribute(ORGANIZATION_IDENTIFIER, extra["identifier"])
        )
    return x509.Name(attributes)


def make_authority(common_name: str = "Test Qualified CA") -> TestAuthority:
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    name = _name(common_name)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return TestAuthority(key, cert)


def _sequence(*parts: bytes) -> bytes:
    body = b"".join(parts)
    return b"\x30" + bytes([len(body)]) + body


def _oid(dotted: str) -> bytes:
    return core.ObjectIdentifier(dotted).dump()


def _qc_statements(*, compliance: bool, seal: bool) -> bytes:
    statements = []
    if compliance:
        statements.append(_sequence(_oid("0.4.0.1862.1.1")))
    if seal:
        statements.append(
            _sequence(_oid("0.4.0.1862.1.6"), _sequence(_oid("0.4.0.1862.1.6.2")))
        )
    return _sequence(*statements)


def make_seal_signer(
    authority: TestAuthority,
    *,
    organization: str = "Universidade do Algarve",
    nipc: str | None = "501413197",
    compliance: bool = True,
    seal: bool = True,
    qualified: bool = True,
    valid_days: int = 365,
) -> signers.SimpleSigner:
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    identifier = f"VATPT-{nipc}" if nipc else None
    builder = (
        x509.CertificateBuilder()
        .subject_name(
            _name("Test Seal", organization=organization, identifier=identifier)
        )
        .issuer_name(authority.cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    )
    if qualified:
        builder = builder.add_extension(
            x509.UnrecognizedExtension(
                QC_STATEMENTS, _qc_statements(compliance=compliance, seal=seal)
            ),
            critical=False,
        )
    cert = builder.sign(authority.key, hashes.SHA256())
    return signers.SimpleSigner(
        signing_cert=asn1_x509.Certificate.load(
            cert.public_bytes(serialization.Encoding.DER)
        ),
        signing_key=asn1_keys.PrivateKeyInfo.load(
            key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        ),
        cert_registry=SimpleCertificateStore.from_certs(
            [
                asn1_x509.Certificate.load(
                    authority.cert.public_bytes(serialization.Encoding.DER)
                )
            ]
        ),
    )


def build_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with the lines of text, valid enough to be signed and read."""
    commands = ["BT", "/F1 12 Tf", "14 TL", "50 750 Td"]
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) '")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
    ]
    out = BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n" % (len(objects) + 1))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref)
    )
    return out.getvalue()


def sign_pdf(pdf: bytes, signer: signers.SimpleSigner) -> bytes:
    writer = IncrementalPdfFileWriter(BytesIO(pdf))
    output = signers.sign_pdf(
        writer, signers.PdfSignatureMetadata(field_name="Signature1"), signer=signer
    )
    return output.getvalue()


def enrolment_lines(
    name: str, school_year: str, institution: str = "Universidade"
) -> list[str]:
    return [
        institution,
        "Declaracao de matricula",
        f"Declara-se que {name} esta matriculado(a)",
        f"no ano letivo {school_year}.",
    ]
