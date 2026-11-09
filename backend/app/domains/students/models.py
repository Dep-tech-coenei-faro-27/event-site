from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProofStatus(StrEnum):
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProofEventKind(StrEnum):
    SUBMITTED = "submitted"
    AUTO_VERIFIED = "auto_verified"
    VIEWED = "viewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NIPC_REGISTERED = "nipc_registered"


class StudentProof(Base):
    """A proof of enrolment. The file is deleted once decided; the hash stays."""

    __tablename__ = "student_proofs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted', 'verified', 'rejected')",
            name="ck_student_proofs_status",
        ),
        CheckConstraint(
            "file_kind IN ('pdf', 'jpg', 'png')", name="ck_student_proofs_file_kind"
        ),
        CheckConstraint("length(file_hash) = 64", name="ck_student_proofs_file_hash"),
        # One active proof per person.
        Index(
            "uq_student_proofs_one_active",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'submitted'"),
            sqlite_where=text("status = 'submitted'"),
        ),
        # The same file cannot verify two accounts.
        Index(
            "uq_student_proofs_verified_hash",
            "file_hash",
            unique=True,
            postgresql_where=text("status = 'verified'"),
            sqlite_where=text("status = 'verified'"),
        ),
        Index("ix_student_proofs_file_hash", "file_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ProofStatus] = mapped_column(
        String(20), default=ProofStatus.SUBMITTED
    )
    file_kind: Mapped[str] = mapped_column(String(3))
    file_hash: Mapped[str] = mapped_column(String(64))
    # Name of the file inside STUDENT_PROOF_DIR; NULL once the file was deleted.
    file_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # What the pre-validation found, without personal data (see prevalidation.py).
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class StudentProofEvent(Base):
    """Who did what to a proof. Never holds personal data."""

    __tablename__ = "student_proof_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    proof_id: Mapped[int] = mapped_column(
        ForeignKey("student_proofs.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[ProofEventKind] = mapped_column(String(20))
    actor: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InstitutionNipc(Base):
    """A tax number known to belong to an institution (learned when approving)."""

    __tablename__ = "institution_nipcs"
    __table_args__ = (
        CheckConstraint("length(nipc) = 9", name="ck_institution_nipcs_nipc"),
    )

    nipc: Mapped[str] = mapped_column(String(9), primary_key=True)
    institution: Mapped[str] = mapped_column(String(40), index=True)
    registered_by: Mapped[str] = mapped_column(String(64))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    proof_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("student_proofs.id", ondelete="SET NULL"), nullable=True
    )
