import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domains.students import review
from app.domains.students.models import (
    InstitutionNipc,
    ProofEventKind,
    ProofStatus,
    StudentProofEvent,
)
from app.domains.users.models import StudentVerificationStatus
from tests.helpers import authenticate
from tests.student_fixtures import (  # noqa: F401
    NIPC,
    ana,
    authority,
    known_nipc,
    proof_of,
    proof_settings,
    send,
    signed_proof,
    signer,
    status_of,
    stored_files,
)

pytestmark = pytest.mark.usefixtures("proof_settings")


@pytest.fixture(autouse=True)
def review_session(monkeypatch, test_engine):
    monkeypatch.setattr(
        review,
        "SessionLocal",
        sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False),
    )


def run(*argv):
    return review.run(["--reviewer", "revisora", *argv])


@pytest.fixture
def waiting(auth_client, db_session, ana, signer):
    """A proof of a new tax number, waiting for a person."""
    send(auth_client, signed_proof(signer))
    return proof_of(db_session, ana)


def test_list_shows_what_waits_and_why(waiting, capsys):
    assert run("list") == 0

    out = capsys.readouterr().out
    assert str(waiting.id) in out
    assert "NIPC novo" in out
    assert "Ana" not in out


def test_list_is_empty_when_nothing_waits(db_session, capsys):
    assert run("list") == 0
    assert capsys.readouterr().out == ""


def test_show_prints_the_signature_facts_and_no_personal_data(waiting, capsys):
    assert run("show", str(waiting.id)) == 0

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["signer_nipc"] == NIPC
    assert data["signer_organization"] == "Universidade do Algarve"
    assert data["qualified_seal"] is True
    assert data["suggested_institution"] == "UALG"
    assert "Ana" not in out
    assert "ana@gmail.com" not in out


def test_show_of_a_missing_proof_fails(capsys):
    assert run("show", "999") == 1


def test_export_copies_the_file_and_records_who_saw_it(waiting, db_session, tmp_path):
    destination = tmp_path / "copy.pdf"

    assert run("export", str(waiting.id), str(destination)) == 0

    assert destination.read_bytes().startswith(b"%PDF-")
    db_session.expire_all()
    viewed = db_session.scalars(
        select(StudentProofEvent).where(StudentProofEvent.kind == ProofEventKind.VIEWED)
    ).all()
    assert [(event.proof_id, event.actor) for event in viewed] == [
        (waiting.id, "revisora")
    ]


def test_a_new_nipc_needs_the_institution_to_approve(waiting, db_session, ana, capsys):
    assert run("approve", str(waiting.id)) == 1

    assert "--institution" in capsys.readouterr().err
    assert status_of(db_session, ana) is StudentVerificationStatus.SUBMITTED


def test_an_unknown_institution_is_refused(waiting, db_session, ana):
    assert run("approve", str(waiting.id), "--institution", "NOPE") == 1

    assert status_of(db_session, ana) is StudentVerificationStatus.SUBMITTED


def test_approving_registers_the_nipc_and_deletes_the_file(
    waiting, db_session, ana, proof_settings
):
    assert run("approve", str(waiting.id), "--institution", "UALG") == 0

    assert status_of(db_session, ana) is StudentVerificationStatus.VERIFIED
    proof = proof_of(db_session, ana)
    assert proof.status == ProofStatus.VERIFIED
    assert proof.decided_by == "revisora"
    assert proof.file_name is None
    assert stored_files(proof_settings) == []
    known = db_session.get(InstitutionNipc, NIPC)
    assert (known.institution, known.registered_by, known.proof_id) == (
        "UALG",
        "revisora",
        proof.id,
    )
    kinds = [event.kind for event in db_session.scalars(select(StudentProofEvent))]
    assert ProofEventKind.APPROVED in kinds
    assert ProofEventKind.NIPC_REGISTERED in kinds


def test_after_approving_the_nipc_is_known_for_the_next_student(
    waiting, auth_client, email_sender, db_session, signer
):
    run("approve", str(waiting.id), "--institution", "UALG")

    auth_client.cookies.clear()
    bia = authenticate(auth_client, email_sender, db_session, email="bia@gmail.com")
    response = send(auth_client, signed_proof(signer, name="Ana Silva"))

    assert response.json() == {"status": "verified"}
    assert status_of(db_session, bia) is StudentVerificationStatus.VERIFIED


def test_rejecting_deletes_the_file_and_keeps_the_hash(
    waiting, db_session, ana, proof_settings
):
    assert run("reject", str(waiting.id)) == 0

    assert status_of(db_session, ana) is StudentVerificationStatus.REJECTED
    proof = proof_of(db_session, ana)
    assert (proof.status, proof.file_name) == (ProofStatus.REJECTED, None)
    assert len(proof.file_hash) == 64
    assert stored_files(proof_settings) == []
    assert db_session.scalar(select(InstitutionNipc)) is None


def test_a_proof_cannot_be_decided_twice(waiting, capsys):
    assert run("reject", str(waiting.id)) == 0

    assert run("approve", str(waiting.id), "--institution", "UALG") == 1
    assert run("reject", str(waiting.id)) == 1


def test_the_same_nipc_cannot_go_to_two_institutions(
    auth_client, email_sender, db_session, ana, signer, waiting
):
    auth_client.cookies.clear()
    bia = authenticate(auth_client, email_sender, db_session, email="bia@gmail.com")
    send(auth_client, signed_proof(signer, name="Bia Costa"))
    second = proof_of(db_session, bia)
    assert run("approve", str(waiting.id), "--institution", "UALG") == 0

    assert run("approve", str(second.id), "--institution", "UPORTO") == 1

    assert status_of(db_session, bia) is StudentVerificationStatus.SUBMITTED
    assert db_session.get(InstitutionNipc, NIPC).institution == "UALG"
