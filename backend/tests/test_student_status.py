"""The numbers the monitoring reads about the proofs of enrolment."""

from datetime import UTC, datetime, timedelta

from app.domains.students.models import ProofStatus, StudentProof
from app.domains.students.status import proofs_waiting
from tests.student_fixtures import ana, proof_settings  # noqa: F401

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def add_proof(db_session, user, status, submitted_at):
    proof = StudentProof(
        user_id=user.id,
        status=status,
        file_kind="pdf",
        file_hash="a" * 64,
        report={},
        submitted_at=submitted_at,
    )
    db_session.add(proof)
    db_session.commit()
    return proof


def test_nothing_waits_when_there_are_no_proofs(db_session):
    assert proofs_waiting(db_session, now=NOW) == {
        "waiting": 0,
        "oldest_waiting_seconds": 0,
    }


def test_it_counts_only_the_proofs_nobody_decided_and_dates_the_oldest(db_session, ana):
    add_proof(db_session, ana, ProofStatus.SUBMITTED, NOW - timedelta(minutes=90))
    add_proof(db_session, ana, ProofStatus.REJECTED, NOW - timedelta(hours=10))

    assert proofs_waiting(db_session, now=NOW) == {
        "waiting": 1,
        "oldest_waiting_seconds": 90 * 60,
    }


def test_a_decided_proof_is_not_counted(db_session, ana):
    add_proof(db_session, ana, ProofStatus.VERIFIED, NOW - timedelta(hours=5))

    assert proofs_waiting(db_session, now=NOW)["waiting"] == 0
