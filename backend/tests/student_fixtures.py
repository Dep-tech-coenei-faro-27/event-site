"""Fixtures and helpers shared by the tests of the proof of enrolment."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.domains.students.document import current_school_year_start
from app.domains.students.models import InstitutionNipc, StudentProof
from app.domains.users.models import StudentVerificationStatus, User
from tests.helpers import authenticate
from tests.student_pdfs import (
    build_pdf,
    enrolment_lines,
    make_authority,
    make_seal_signer,
    sign_pdf,
)

PROOF_URL = "/api/users/me/student-proof"
NIPC = "501413197"
OTHER_NIPC = "502011378"
ORGANIZATION = "Universidade do Algarve"
SCHOOL_YEAR = (
    f"{current_school_year_start(datetime.now(UTC))}/"
    f"{current_school_year_start(datetime.now(UTC)) + 1}"
)
OLD_YEAR = "2019/2020"


@pytest.fixture
def authority():
    return make_authority()


@pytest.fixture
def proof_settings(monkeypatch, tmp_path, authority):
    anchors = tmp_path / "anchors.pem"
    anchors.write_bytes(authority.pem)
    folder = tmp_path / "proofs"
    monkeypatch.setattr(settings, "STUDENT_TRUST_ANCHORS_FILE", anchors)
    monkeypatch.setattr(settings, "STUDENT_PROOF_DIR", folder)
    monkeypatch.setattr(settings, "STUDENT_EMAIL_DOMAINS", [])
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    return folder


@pytest.fixture
def signer(authority):
    return make_seal_signer(authority, organization=ORGANIZATION, nipc=NIPC)


@pytest.fixture
def known_nipc(db_session):
    db_session.add(InstitutionNipc(nipc=NIPC, institution="UALG", registered_by="test"))
    db_session.commit()


def signed_proof(signer, *, name="Ana Silva", year=SCHOOL_YEAR) -> bytes:
    return sign_pdf(build_pdf(enrolment_lines(name, year)), signer)


def send(client, data: bytes, *, filename="declaracao.pdf", content_type=None):
    return client.post(
        PROOF_URL,
        files={"file": (filename, data, content_type or "application/pdf")},
    )


def proof_of(db_session, user) -> StudentProof:
    db_session.expire_all()
    return db_session.scalar(
        select(StudentProof)
        .where(StudentProof.user_id == user.id)
        .order_by(StudentProof.id.desc())
    )


def status_of(db_session, user) -> StudentVerificationStatus:
    db_session.expire_all()
    return db_session.get(User, user.id).student_verification_status


def stored_files(folder: Path) -> list[Path]:
    return list(folder.glob("*")) if folder.exists() else []


@pytest.fixture
def ana(auth_client, email_sender, db_session):
    return authenticate(auth_client, email_sender, db_session, email="ana@gmail.com")
