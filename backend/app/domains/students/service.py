import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.students.document import DocumentFindings, inspect_pdf
from app.domains.students.institutions import institution_by_key, match_institution
from app.domains.students.models import (
    InstitutionNipc,
    ProofEventKind,
    ProofStatus,
    StudentProof,
    StudentProofEvent,
)
from app.domains.users.models import StudentVerificationStatus, User

logger = logging.getLogger(__name__)

SYSTEM_ACTOR = "system"
SIGNATURES = (
    (b"%PDF-", "pdf"),
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
)
# The checks that must all pass for a proof to be approved without a person.
AUTO_APPROVAL_CHECKS = (
    "signature_intact",
    "qualified_seal",
    "institution_known",
    "name_found",
    "school_year_current",
    "file_not_reused",
)


class ProofError(Exception):
    """Base of the errors the endpoint turns into answers."""


class UnsupportedFileError(ProofError):
    """The file is not a PDF, JPEG or PNG, whatever its name or type says."""


class AlreadyVerifiedError(ProofError):
    """The account is already a verified student."""


class ProofAlreadySubmittedError(ProofError):
    """The account already has a proof waiting for a decision."""


class ProofAlreadyDecidedError(ProofError):
    """Someone else decided the proof first."""


class FileAlreadyUsedError(ProofError):
    """The same file already verified another account."""


class NipcConflictError(ProofError):
    """The tax number already belongs to another institution."""


def sniff_kind(data: bytes) -> str | None:
    """The kind of file by its first bytes (the name and declared type are ignored)."""
    for prefix, kind in SIGNATURES:
        if data.startswith(prefix):
            return kind
    return None


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def proof_path(file_name: str) -> Path:
    return settings.STUDENT_PROOF_DIR / file_name


def _store_file(data: bytes) -> str:
    directory = settings.STUDENT_PROOF_DIR
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = secrets.token_hex(16)
    descriptor = os.open(
        directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode=0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    return name


def _delete_file(name: str | None) -> None:
    if not name:
        return
    try:
        proof_path(name).unlink(missing_ok=True)
    except OSError:
        logger.error("A student proof file could not be deleted")


def _event(db: Session, proof: StudentProof, kind: ProofEventKind, actor: str) -> None:
    db.add(StudentProofEvent(proof_id=proof.id, kind=kind, actor=actor))


def registered_institution(db: Session, nipc: str | None) -> str | None:
    if nipc is None:
        return None
    return db.scalar(
        select(InstitutionNipc.institution).where(InstitutionNipc.nipc == nipc)
    )


def build_report(
    db: Session, findings: DocumentFindings, digest: str, user_id: int
) -> dict:
    """The facts about a proof, without personal data, for the automatic decision."""
    known = registered_institution(db, findings.signer_nipc)
    institution = known
    if institution is None and findings.qualified_seal:
        matched = match_institution(findings.signer_organization or "")
        institution = matched.key if matched else None
    reused = (
        db.scalar(
            select(StudentProof.id)
            .where(StudentProof.file_hash == digest, StudentProof.user_id != user_id)
            .limit(1)
        )
        is not None
    )
    report = {
        "signed": findings.signed,
        "signature_intact": findings.signature_intact,
        "qualified_seal": findings.qualified_seal,
        "signer_nipc": findings.signer_nipc if findings.qualified_seal else None,
        "signer_organization": (
            findings.signer_organization if findings.qualified_seal else None
        ),
        "institution": institution,
        "institution_known": known is not None,
        "new_nipc": known is None and findings.signer_nipc is not None,
        "name_found": findings.name_found,
        "school_year_current": findings.school_year_current,
        "file_not_reused": not reused,
        "reasons": list(findings.reasons),
    }
    if reused:
        report["reasons"].append("file_reused")
    if known is None and findings.qualified_seal:
        report["reasons"].append(
            "new_nipc" if findings.signer_nipc else "no_nipc_in_seal"
        )
    return report


def passes_automatic_checks(report: dict) -> bool:
    return all(report.get(check) is True for check in AUTO_APPROVAL_CHECKS)


def _lock_user(db: Session, user_id: int) -> User:
    return db.execute(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()


def submit_proof(
    db: Session, user: User, data: bytes, now: datetime | None = None
) -> StudentProof:
    """Keep the file, read it and, if everything checks out, approve it on the spot.

    Anything that does not pass waits for a person (``python -m
    app.domains.students.review``).
    """
    now = now or datetime.now(UTC)
    kind = sniff_kind(data)
    if kind is None:
        raise UnsupportedFileError

    digest = file_hash(data)
    findings = (
        inspect_pdf(data, user.name, now)
        if kind == "pdf"
        else DocumentFindings(reasons=["not_a_pdf"])
    )

    user_id = user.id
    locked = _lock_user(db, user_id)
    if locked.student_verification_status is StudentVerificationStatus.VERIFIED:
        db.rollback()
        raise AlreadyVerifiedError
    if locked.student_verification_status is StudentVerificationStatus.SUBMITTED:
        db.rollback()
        raise ProofAlreadySubmittedError

    report = build_report(db, findings, digest, user_id)
    stored = _store_file(data)
    proof = StudentProof(
        user_id=user_id,
        status=ProofStatus.SUBMITTED,
        file_kind=kind,
        file_hash=digest,
        file_name=stored,
        report=report,
        submitted_at=now,
    )
    locked.student_verification_status = StudentVerificationStatus.SUBMITTED
    db.add(proof)
    try:
        db.flush()
        _event(db, proof, ProofEventKind.SUBMITTED, SYSTEM_ACTOR)
        db.commit()
    except IntegrityError:
        db.rollback()
        _delete_file(stored)
        raise ProofAlreadySubmittedError from None
    except Exception:
        db.rollback()
        _delete_file(stored)
        raise

    if passes_automatic_checks(report):
        try:
            approve_proof(db, proof.id, SYSTEM_ACTOR, automatic=True)
        except FileAlreadyUsedError:
            # Another account was approved with this file in the meantime.
            proof = db.get(StudentProof, proof.id)
            proof.report = {
                **report,
                "file_not_reused": False,
                "reasons": [*report["reasons"], "file_reused"],
            }
            db.commit()
        except ProofError:
            logger.info("A student proof was left for manual review")
    db.refresh(proof)
    return proof


def _decide(
    db: Session,
    proof_id: int,
    actor: str,
    new_status: ProofStatus,
    event_kind: ProofEventKind,
    *,
    register: tuple[str, str] | None = None,
) -> StudentProof:
    proof = db.get(StudentProof, proof_id)
    if proof is None:
        raise ProofAlreadyDecidedError
    now = datetime.now(UTC)
    file_name = proof.file_name
    user_status = (
        StudentVerificationStatus.VERIFIED
        if new_status is ProofStatus.VERIFIED
        else StudentVerificationStatus.REJECTED
    )
    try:
        # Whoever changes the status first wins; the other finds no row to change.
        claimed = db.execute(
            update(StudentProof)
            .where(
                StudentProof.id == proof_id,
                StudentProof.status == ProofStatus.SUBMITTED,
            )
            .values(status=new_status, decided_at=now, decided_by=actor, file_name=None)
        ).rowcount
        if claimed != 1:
            db.rollback()
            raise ProofAlreadyDecidedError
        values = {"student_verification_status": user_status}
        if new_status is ProofStatus.VERIFIED:
            values["student_verified_at"] = now
        db.execute(update(User).where(User.id == proof.user_id).values(**values))
        _event(db, proof, event_kind, actor)
        if register is not None:
            nipc, institution = register
            existing = db.get(InstitutionNipc, nipc)
            if existing is None:
                db.add(
                    InstitutionNipc(
                        nipc=nipc,
                        institution=institution,
                        registered_by=actor,
                        proof_id=proof.id,
                    )
                )
                _event(db, proof, ProofEventKind.NIPC_REGISTERED, actor)
            elif existing.institution != institution:
                db.rollback()
                raise NipcConflictError
        db.commit()
    except IntegrityError:
        db.rollback()
        raise FileAlreadyUsedError from None
    _delete_file(file_name)
    db.refresh(proof)
    return proof


def approve_proof(
    db: Session,
    proof_id: int,
    actor: str,
    *,
    automatic: bool = False,
    institution: str | None = None,
) -> StudentProof:
    register = None
    if not automatic:
        proof = db.get(StudentProof, proof_id)
        nipc = (proof.report or {}).get("signer_nipc") if proof else None
        if institution is not None and nipc is not None:
            if institution_by_key(institution) is None:
                raise ValueError("unknown institution")
            register = (nipc, institution)
    return _decide(
        db,
        proof_id,
        actor,
        ProofStatus.VERIFIED,
        ProofEventKind.AUTO_VERIFIED if automatic else ProofEventKind.APPROVED,
        register=register,
    )


def reject_proof(db: Session, proof_id: int, actor: str) -> StudentProof:
    return _decide(db, proof_id, actor, ProofStatus.REJECTED, ProofEventKind.REJECTED)


def record_view(db: Session, proof: StudentProof, actor: str) -> None:
    _event(db, proof, ProofEventKind.VIEWED, actor)
    db.commit()


def waiting_proofs(db: Session) -> list[StudentProof]:
    return list(
        db.scalars(
            select(StudentProof)
            .where(StudentProof.status == ProofStatus.SUBMITTED)
            .order_by(StudentProof.submitted_at, StudentProof.id)
        )
    )
