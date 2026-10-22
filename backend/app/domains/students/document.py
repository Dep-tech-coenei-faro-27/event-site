"""What a proof of enrolment says, read from the file.

Nothing here touches the database. The findings hold no personal data: they say that
the name was found, not what it is.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from asn1crypto import core, pem
from asn1crypto import x509 as asn1_x509
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.diff_analysis import ModificationLevel
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.status import SignatureCoverageLevel
from pyhanko_certvalidator import ValidationContext
from pypdf import PdfReader

from app.core.config import settings
from app.domains.students.institutions import is_valid_nipc, normalize

logger = logging.getLogger(__name__)

# pyHanko writes the name of the certificate holder in its validation errors. A
# signature that is not an institution's seal is a person's, so none of it may reach
# the logs.
for _noisy in ("pyhanko", "pyhanko_certvalidator"):
    logging.getLogger(_noisy).setLevel(logging.CRITICAL)

DEFAULT_TRUST_ANCHORS = Path(__file__).parent / "trust" / "eu_qualified_seals.pem"
MAX_TEXT_PAGES = 5
MAX_TEXT_CHARS = 200_000

QC_STATEMENTS_OID = "1.3.6.1.5.5.7.1.3"
QC_COMPLIANCE_OID = "0.4.0.1862.1.1"
QC_TYPE_OID = "0.4.0.1862.1.6"
QC_TYPE_SEAL_OID = "0.4.0.1862.1.6.2"
ORGANIZATION_IDENTIFIER_OID = "2.5.4.97"
NIPC_IDENTIFIER = re.compile(r"(?:VAT|NTR)PT-?(\d{9})")
SCHOOL_YEAR = re.compile(r"(?<!\d)(20\d{2})\s*[/\-–]\s*(?:20)?(\d{2})(?!\d)")
SCHOOL_YEAR_STARTS_IN_MONTH = 8


class _QcStatement(core.Sequence):
    _fields = [
        ("statement_id", core.ObjectIdentifier),
        ("statement_info", core.Any, {"optional": True}),
    ]


class _QcStatements(core.SequenceOf):
    _child_spec = _QcStatement


class _QcTypes(core.SequenceOf):
    _child_spec = core.ObjectIdentifier


@dataclass
class DocumentFindings:
    """Results of reading one proof; ``reasons`` explains whatever failed."""

    signed: bool = False
    signature_intact: bool = False
    qualified_seal: bool = False
    signer_nipc: str | None = None
    signer_organization: str | None = None
    name_found: bool = False
    school_year_current: bool = False
    reasons: list[str] = field(default_factory=list)


@lru_cache(maxsize=4)
def _read_trust_anchors(
    path: Path, modified: float
) -> tuple[asn1_x509.Certificate, ...]:
    anchors = []
    with path.open("rb") as handle:
        for _, _, der in pem.unarmor(handle.read(), multiple=True):
            anchors.append(asn1_x509.Certificate.load(der))
    return tuple(anchors)


def load_trust_anchors() -> tuple[asn1_x509.Certificate, ...]:
    path = settings.STUDENT_TRUST_ANCHORS_FILE or DEFAULT_TRUST_ANCHORS
    try:
        return _read_trust_anchors(path, path.stat().st_mtime)
    except (OSError, ValueError):
        logger.error("The trust anchors of the student proofs could not be read")
        return ()


def current_school_year_start(now: datetime) -> int:
    return now.year if now.month >= SCHOOL_YEAR_STARTS_IN_MONTH else now.year - 1


def _is_qualified_seal(cert: asn1_x509.Certificate) -> bool:
    for extension in cert["tbs_certificate"]["extensions"] or []:
        if extension["extn_id"].dotted != QC_STATEMENTS_OID:
            continue
        compliant = False
        seal = False
        statements = _QcStatements.load(extension["extn_value"].contents)
        for statement in statements:
            statement_id = statement["statement_id"].dotted
            if statement_id == QC_COMPLIANCE_OID:
                compliant = True
            elif (
                statement_id == QC_TYPE_OID and statement["statement_info"] is not None
            ):
                types = _QcTypes.load(statement["statement_info"].dump())
                seal = any(item.dotted == QC_TYPE_SEAL_OID for item in types)
        return compliant and seal
    return False


def _subject_attribute(cert: asn1_x509.Certificate, dotted: str) -> str | None:
    for rdn in cert.subject.chosen:
        for item in rdn:
            if item["type"].dotted == dotted:
                return str(item["value"].native)
    return None


def _signer_nipc(cert: asn1_x509.Certificate) -> str | None:
    identifier = _subject_attribute(cert, ORGANIZATION_IDENTIFIER_OID)
    match = NIPC_IDENTIFIER.fullmatch((identifier or "").strip().upper())
    if match and is_valid_nipc(match.group(1)):
        return match.group(1)
    return None


def _entire_file(status) -> bool:
    if status.coverage is SignatureCoverageLevel.ENTIRE_FILE:
        return True
    return (
        status.coverage is SignatureCoverageLevel.ENTIRE_REVISION
        and status.modification_level is ModificationLevel.LTA_UPDATES
    )


def _check_signatures(data: bytes, findings: DocumentFindings) -> None:
    anchors = load_trust_anchors()
    context = ValidationContext(
        trust_roots=anchors, allow_fetching=False, revocation_mode="soft-fail"
    )
    reader = PdfFileReader(BytesIO(data), strict=False)
    signatures = list(reader.embedded_signatures)
    if not signatures:
        findings.reasons.append("no_signature")
        return
    findings.signed = True

    for embedded in signatures:
        try:
            status = validate_pdf_signature(embedded, signer_validation_context=context)
        except Exception:
            logger.info("A signature of a student proof could not be validated")
            continue
        if not (status.intact and status.valid):
            continue
        cert = embedded.signer_cert
        # The signature is sound. Whether it can be trusted is a separate question.
        findings.signature_intact = _entire_file(status)
        if not (status.trusted and findings.signature_intact):
            continue
        if not _is_qualified_seal(cert):
            findings.reasons.append("not_a_qualified_seal")
            return
        findings.qualified_seal = True
        findings.signer_nipc = _signer_nipc(cert)
        findings.signer_organization = _subject_attribute(cert, "2.5.4.10")
        return
    if not findings.signature_intact:
        findings.reasons.append("signature_not_intact")
    elif not findings.qualified_seal:
        findings.reasons.append("signature_not_trusted")


def _extract_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data), strict=False)
    parts: list[str] = []
    total = 0
    for page in reader.pages[:MAX_TEXT_PAGES]:
        text = page.extract_text() or ""
        parts.append(text)
        total += len(text)
        if total > MAX_TEXT_CHARS:
            break
    return "\n".join(parts)[:MAX_TEXT_CHARS]


def name_in_text(account_name: str, text: str) -> bool:
    """Every word of the account name appears as a word of the document."""
    words = {word for word in normalize(account_name).split() if len(word) > 1}
    if not words:
        return False
    return words <= set(normalize(text).split())


def school_year_in_text(text: str, now: datetime) -> bool:
    start = current_school_year_start(now)
    for first, second in SCHOOL_YEAR.findall(text):
        if int(first) == start and int(second) == (start + 1) % 100:
            return True
    return False


def inspect_pdf(data: bytes, account_name: str, now: datetime) -> DocumentFindings:
    findings = DocumentFindings()
    try:
        _check_signatures(data, findings)
    except Exception:
        logger.info("A student proof PDF could not be read")
        findings.reasons.append("unreadable_pdf")
        return findings

    try:
        text = _extract_text(data)
    except Exception:
        logger.info("The text of a student proof PDF could not be read")
        findings.reasons.append("unreadable_text")
        return findings
    findings.name_found = name_in_text(account_name, text)
    findings.school_year_current = school_year_in_text(text, now)
    if not findings.name_found:
        findings.reasons.append("name_not_found")
    if not findings.school_year_current:
        findings.reasons.append("school_year_not_current")
    return findings
