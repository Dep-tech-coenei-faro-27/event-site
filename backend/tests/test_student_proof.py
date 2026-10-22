import logging
import threading
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.middleware import STUDENT_PROOF_PATH
from app.domains.students.document import current_school_year_start, name_in_text
from app.domains.students.models import (
    ProofEventKind,
    ProofStatus,
    StudentProof,
    StudentProofEvent,
)
from app.domains.students.service import (
    FileAlreadyUsedError,
    ProofAlreadyDecidedError,
    ProofAlreadySubmittedError,
    approve_proof,
    file_hash,
    reject_proof,
    submit_proof,
)
from app.domains.users.models import StudentVerificationStatus, User
from tests.conftest import TEST_DATABASE_URL
from tests.helpers import ME_URL, authenticate
from tests.student_fixtures import (  # noqa: F401
    NIPC,
    OLD_YEAR,
    ORGANIZATION,
    PROOF_URL,
    SCHOOL_YEAR,
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
from tests.student_pdfs import (
    build_pdf,
    enrolment_lines,
    make_authority,
    make_seal_signer,
    sign_pdf,
)

pytestmark = pytest.mark.usefixtures("proof_settings")

# --- the proof is checked and, if everything passes, approved on its own -------------


def test_a_signed_proof_that_passes_everything_is_approved_on_its_own(
    auth_client, db_session, ana, signer, known_nipc, proof_settings
):
    response = send(auth_client, signed_proof(signer))

    assert response.status_code == 201
    assert response.json() == {"status": "verified"}
    assert status_of(db_session, ana) is StudentVerificationStatus.VERIFIED
    assert db_session.get(User, ana.id).student_verified_at is not None
    proof = proof_of(db_session, ana)
    assert proof.status == ProofStatus.VERIFIED
    assert proof.decided_by == "system"
    assert proof.report["institution"] == "UALG"


def test_the_file_is_deleted_after_the_decision_and_the_hash_stays(
    auth_client, db_session, ana, signer, known_nipc, proof_settings
):
    data = signed_proof(signer)

    send(auth_client, data)

    proof = proof_of(db_session, ana)
    assert proof.file_name is None
    assert proof.file_hash == file_hash(data)
    assert stored_files(proof_settings) == []


def test_me_shows_every_state(auth_client, db_session, ana, signer, known_nipc):
    assert auth_client.get(ME_URL).json()["student_verification_status"] == "none"

    send(auth_client, signed_proof(signer, name="Outra Pessoa"))
    assert auth_client.get(ME_URL).json()["student_verification_status"] == "submitted"

    reject_proof(db_session, proof_of(db_session, ana).id, "revisor")
    assert auth_client.get(ME_URL).json()["student_verification_status"] == "rejected"

    send(auth_client, signed_proof(signer))
    assert auth_client.get(ME_URL).json()["student_verification_status"] == "verified"


def test_the_events_hold_no_personal_data(
    auth_client, db_session, ana, signer, known_nipc
):
    send(auth_client, signed_proof(signer))

    events = db_session.scalars(select(StudentProofEvent)).all()
    assert [event.kind for event in events] == [
        ProofEventKind.SUBMITTED,
        ProofEventKind.AUTO_VERIFIED,
    ]
    assert {event.actor for event in events} == {"system"}
    assert "Ana" not in str(proof_of(db_session, ana).report)


# --- what sends a proof to a person ---------------------------------------------------


def waits_for_review(client, db_session, user, data, reason, filename="d.pdf"):
    response = send(client, data, filename=filename)
    assert response.status_code == 201
    assert response.json() == {"status": "submitted"}
    proof = proof_of(db_session, user)
    assert proof.status == ProofStatus.SUBMITTED
    assert proof.file_name is not None
    assert reason in proof.report["reasons"]
    return proof


def test_a_tampered_pdf_waits_for_review(
    auth_client, db_session, ana, signer, known_nipc
):
    data = signed_proof(signer).replace(b"Ana Silva", b"Ana Silvo")

    proof = waits_for_review(auth_client, db_session, ana, data, "signature_not_intact")

    assert proof.report["signature_intact"] is False


def test_a_pdf_with_content_added_after_signing_waits_for_review(
    auth_client, db_session, ana, signer, known_nipc
):
    waits_for_review(
        auth_client,
        db_session,
        ana,
        signed_proof(signer) + b"\n% added later\n",
        "signature_not_intact",
    )


def test_a_pdf_without_signature_waits_for_review(
    auth_client, db_session, ana, known_nipc
):
    data = build_pdf(enrolment_lines("Ana Silva", SCHOOL_YEAR))

    waits_for_review(auth_client, db_session, ana, data, "no_signature")


def test_a_signature_from_an_unknown_authority_waits_for_review(
    auth_client, db_session, ana, known_nipc
):
    stranger = make_seal_signer(make_authority(), organization=ORGANIZATION, nipc=NIPC)

    waits_for_review(
        auth_client,
        db_session,
        ana,
        signed_proof(stranger),
        "signature_not_trusted",
    )


def test_a_signature_that_is_not_a_qualified_seal_waits_for_review(
    auth_client, db_session, ana, authority, known_nipc
):
    plain = make_seal_signer(
        authority, organization=ORGANIZATION, nipc=NIPC, seal=False
    )

    waits_for_review(
        auth_client, db_session, ana, signed_proof(plain), "not_a_qualified_seal"
    )


def test_a_new_nipc_waits_for_review(auth_client, db_session, ana, signer):
    proof = waits_for_review(
        auth_client, db_session, ana, signed_proof(signer), "new_nipc"
    )

    assert proof.report["new_nipc"] is True
    assert proof.report["signer_nipc"] == NIPC


def test_a_different_name_waits_for_review(
    auth_client, db_session, ana, signer, known_nipc
):
    waits_for_review(
        auth_client,
        db_session,
        ana,
        signed_proof(signer, name="Maria Costa"),
        "name_not_found",
    )


def test_an_old_school_year_waits_for_review(
    auth_client, db_session, ana, signer, known_nipc
):
    waits_for_review(
        auth_client,
        db_session,
        ana,
        signed_proof(signer, year=OLD_YEAR),
        "school_year_not_current",
    )


def test_a_short_form_of_the_school_year_is_accepted(
    auth_client, db_session, ana, signer, known_nipc
):
    start = current_school_year_start(datetime.now(UTC))
    short = f"{start}-{(start + 1) % 100:02d}"

    response = send(auth_client, signed_proof(signer, year=short))

    assert response.json() == {"status": "verified"}


@pytest.mark.parametrize(
    ("data", "filename", "content_type"),
    [
        (b"\xff\xd8\xff\xe0" + b"0" * 100, "foto.jpg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n" + b"0" * 100, "foto.png", "image/png"),
    ],
)
def test_an_image_always_waits_for_review(
    auth_client, db_session, ana, known_nipc, data, filename, content_type
):
    response = send(auth_client, data, filename=filename, content_type=content_type)

    assert response.json() == {"status": "submitted"}
    proof = proof_of(db_session, ana)
    assert proof.file_kind == filename[-3:]
    assert "not_a_pdf" in proof.report["reasons"]


def test_the_same_file_in_two_accounts_waits_for_review_in_the_second(
    auth_client, email_sender, db_session, ana, signer, known_nipc
):
    data = signed_proof(signer, name="Ana Silva")
    assert send(auth_client, data).json() == {"status": "verified"}

    auth_client.cookies.clear()
    bia = authenticate(auth_client, email_sender, db_session, email="bia@gmail.com")
    response = send(auth_client, data)

    assert response.json() == {"status": "submitted"}
    proof = proof_of(db_session, bia)
    assert proof.report["file_not_reused"] is False
    assert "file_reused" in proof.report["reasons"]
    with pytest.raises(FileAlreadyUsedError):
        approve_proof(db_session, proof.id, "revisor")
    assert status_of(db_session, bia) is StudentVerificationStatus.SUBMITTED


# --- the file that arrives ------------------------------------------------------------


def test_the_type_is_decided_by_the_first_bytes_not_by_the_name(
    auth_client, db_session, ana, proof_settings
):
    html = b"<html><script>alert(1)</script></html>"

    response = send(auth_client, html, filename="declaracao.pdf")

    assert response.status_code == 415
    assert status_of(db_session, ana) is StudentVerificationStatus.NONE
    assert stored_files(proof_settings) == []


def test_a_pdf_named_as_an_image_is_still_read_as_a_pdf(
    auth_client, db_session, ana, signer, known_nipc
):
    response = send(
        auth_client, signed_proof(signer), filename="foto.png", content_type="image/png"
    )

    assert response.json() == {"status": "verified"}
    assert proof_of(db_session, ana).file_kind == "pdf"


def test_an_empty_file_is_refused(auth_client, ana):
    assert send(auth_client, b"").status_code == 422


def test_a_file_over_the_limit_is_refused_with_413(
    auth_client, db_session, ana, proof_settings
):
    data = b"%PDF-" + b"0" * settings.STUDENT_PROOF_MAX_BYTES

    response = send(auth_client, data)

    assert response.status_code == 413
    assert stored_files(proof_settings) == []


def test_a_file_of_exactly_the_limit_goes_through_the_request_limit(
    auth_client, db_session, ana
):
    data = b"%PDF-" + b"0" * (settings.STUDENT_PROOF_MAX_BYTES - 5)

    assert len(data) == settings.STUDENT_PROOF_MAX_BYTES
    assert send(auth_client, data).status_code == 201


def test_other_endpoints_keep_the_small_request_limit(auth_client, ana):
    assert STUDENT_PROOF_PATH == PROOF_URL
    response = auth_client.put(
        "/api/users/me", content=b"0" * (settings.MAX_REQUEST_BYTES + 1)
    )

    assert response.status_code == 413


def test_the_file_is_stored_outside_media_and_never_served(
    auth_client, db_session, ana, signer, proof_settings
):
    send(auth_client, signed_proof(signer))
    name = proof_of(db_session, ana).file_name
    media = settings.MEDIA_DIR.resolve()

    assert proof_settings.resolve() != media
    assert media not in proof_settings.resolve().parents
    assert auth_client.get(f"/media/{name}").status_code == 404
    assert auth_client.get(f"/media/../{name}").status_code in (400, 404)


def test_the_private_folder_cannot_be_inside_media():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            JWT_SECRET_KEY="x" * 40,
            ENVIRONMENT="dev",
            STUDENT_PROOF_DIR=settings.MEDIA_DIR / "proofs",
        )


def test_the_stored_file_is_only_readable_by_the_server(
    auth_client, db_session, ana, signer, proof_settings
):
    send(auth_client, signed_proof(signer, name="Outra Pessoa"))

    (path,) = stored_files(proof_settings)
    assert path.stat().st_mode & 0o077 == 0
    assert proof_settings.stat().st_mode & 0o077 == 0


# --- one active proof, accounts, rate limit -------------------------------------------


def test_only_one_active_proof_per_person(auth_client, db_session, ana, signer):
    data = signed_proof(signer, name="Outra Pessoa")
    assert send(auth_client, data).status_code == 201

    again = send(auth_client, signed_proof(signer, name="Outra Pessoa", year=OLD_YEAR))

    assert again.status_code == 409
    count = db_session.scalar(text("SELECT count(*) FROM student_proofs"))
    assert count == 1


def test_a_verified_student_cannot_send_another(
    auth_client, db_session, ana, signer, known_nipc
):
    send(auth_client, signed_proof(signer))

    assert send(auth_client, signed_proof(signer, year=OLD_YEAR)).status_code == 409


def test_a_rejected_person_can_send_again(auth_client, db_session, ana, signer):
    send(auth_client, signed_proof(signer, name="Outra Pessoa"))
    reject_proof(db_session, proof_of(db_session, ana).id, "revisor")

    response = send(
        auth_client, signed_proof(signer, name="Outra Pessoa", year=OLD_YEAR)
    )

    assert response.status_code == 201
    assert status_of(db_session, ana) is StudentVerificationStatus.SUBMITTED


def test_an_institutional_email_student_cannot_send_one(
    auth_client, email_sender, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "STUDENT_EMAIL_DOMAINS", ["ualg.pt"])
    authenticate(auth_client, email_sender, db_session, email="ana@ualg.pt")

    assert send(auth_client, b"%PDF-1.7 x").status_code == 409


def test_it_needs_a_logged_in_verified_account(auth_client):
    assert send(auth_client, b"%PDF-1.7 x").status_code == 401


def test_another_account_does_not_see_or_change_my_proof(
    auth_client, email_sender, db_session, ana, signer
):
    send(auth_client, signed_proof(signer, name="Outra Pessoa"))
    auth_client.cookies.clear()
    bia = authenticate(auth_client, email_sender, db_session, email="bia@gmail.com")

    assert auth_client.get(ME_URL).json()["student_verification_status"] == "none"
    assert status_of(db_session, ana) is StudentVerificationStatus.SUBMITTED
    assert status_of(db_session, bia) is StudentVerificationStatus.NONE
    assert proof_of(db_session, bia) is None


def test_requests_are_limited(auth_client, db_session, ana, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_STUDENT_PROOF_PER_HOUR", 2)

    codes = [send(auth_client, b"not a proof").status_code for _ in range(3)]

    assert codes == [415, 415, 429]


# --- nothing personal in logs or errors -----------------------------------------------


def test_no_personal_data_in_logs_or_errors(
    auth_client, db_session, ana, authority, caplog
):
    caplog.set_level(logging.DEBUG)
    person = make_seal_signer(
        make_authority("Another CA"),
        organization="Ana Silva",
        nipc=None,
        qualified=False,
    )
    data = sign_pdf(build_pdf(enrolment_lines("Ana Silva", SCHOOL_YEAR)), person)

    response = send(auth_client, data)
    broken = send(auth_client, b"%PDF-1.7\n garbage")

    for text_ in (caplog.text, response.text, broken.text):
        assert "Ana Silva" not in text_
        assert "ana@gmail.com" not in text_
    assert proof_of(db_session, ana).report["signer_organization"] is None


# --- concurrency (needs PostgreSQL for real locks) ------------------------------------

needs_postgres = pytest.mark.skipif(
    not (TEST_DATABASE_URL or "").startswith("postgresql"),
    reason="the locks only exist in PostgreSQL",
)


def make_users(db_session, count):
    users = []
    for number in range(count):
        user = User(
            name="Ana Silva",
            email=f"ana{number}@gmail.com",
            password_hash="x",
            is_verified=True,
        )
        db_session.add(user)
        users.append(user)
    db_session.commit()
    return [user.id for user in users]


def run_in_threads(engine, jobs):
    results = [None] * len(jobs)
    barrier = threading.Barrier(len(jobs))

    def work(index, job):
        with Session(bind=engine) as session:
            barrier.wait()
            try:
                results[index] = job(session)
            except Exception as error:
                results[index] = error

    threads = [
        threading.Thread(target=work, args=(index, job))
        for index, job in enumerate(jobs)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


@needs_postgres
def test_two_accounts_sending_the_same_file_at_once_verify_only_one(
    test_engine, db_session, signer, known_nipc
):
    first, second = make_users(db_session, 2)
    data = signed_proof(signer)

    def submit(user_id):
        def job(session):
            return submit_proof(session, session.get(User, user_id), data)

        return job

    run_in_threads(test_engine, [submit(first), submit(second)])

    db_session.expire_all()
    statuses = sorted(
        db_session.scalars(select(StudentProof.status)).all(),
    )
    assert statuses == [ProofStatus.SUBMITTED, ProofStatus.VERIFIED]


@needs_postgres
def test_two_requests_of_the_same_person_at_once_keep_one_proof(
    test_engine, db_session, signer
):
    (user_id,) = make_users(db_session, 1)
    data = signed_proof(signer, name="Outra Pessoa")

    def job(session):
        return submit_proof(session, session.get(User, user_id), data)

    results = run_in_threads(test_engine, [job, job, job])

    assert sum(isinstance(result, StudentProof) for result in results) == 1
    assert (
        sum(isinstance(result, ProofAlreadySubmittedError) for result in results) == 2
    )
    assert db_session.scalar(text("SELECT count(*) FROM student_proofs")) == 1


@needs_postgres
def test_two_reviewers_deciding_at_once_one_wins(test_engine, db_session, signer):
    (user_id,) = make_users(db_session, 1)
    proof = submit_proof(
        db_session,
        db_session.get(User, user_id),
        signed_proof(signer, name="Outra Pessoa"),
    )

    def decide(function):
        return lambda session: function(session, proof.id, "revisor")

    results = run_in_threads(test_engine, [decide(approve_proof), decide(reject_proof)])

    assert sum(isinstance(result, StudentProof) for result in results) == 1
    assert sum(isinstance(result, ProofAlreadyDecidedError) for result in results) == 1
    db_session.expire_all()
    final = db_session.get(StudentProof, proof.id)
    assert (
        db_session.get(User, user_id).student_verification_status.value == final.status
    )


DECLARATION = (
    "Universidade do Algarve declara que Maria Joana Pereira Santos esta matriculada"
)


@pytest.mark.parametrize("name", ["Universidade", "Maria", "Santos", "M Santos", ""])
def test_a_name_with_fewer_than_two_words_is_never_found_in_the_text(name):
    assert name_in_text(name, DECLARATION) is False


@pytest.mark.parametrize(
    "name", ["Maria Santos", "Santos Pereira", "Maria Joana Pereira Santos"]
)
def test_a_name_with_two_or_more_words_found_in_the_text_matches(name):
    assert name_in_text(name, DECLARATION) is True
