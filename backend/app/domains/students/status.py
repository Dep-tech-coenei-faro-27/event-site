"""Read, only, how many proofs of enrolment wait for a person (for the monitoring).

    python -m app.domains.students.status

Prints ``key=value`` lines: ``waiting`` (proofs submitted and not yet decided, by the
system or by a reviewer) and ``oldest_waiting_seconds`` (how long the oldest has
waited, 0 if none): ``scripts/export-metrics.sh`` turns the numbers into metrics and
``monitoring/alerts.yml`` into an alert that goes to Discord. Nothing is changed and
nothing about a person is printed.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.domains.students.models import ProofStatus, StudentProof


def proofs_waiting(db, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    waiting, oldest = db.execute(
        select(func.count(), func.min(StudentProof.submitted_at)).where(
            StudentProof.status == ProofStatus.SUBMITTED
        )
    ).one()
    seconds = 0
    if oldest is not None:
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=UTC)
        seconds = max(0, int((now - oldest).total_seconds()))
    return {"waiting": int(waiting or 0), "oldest_waiting_seconds": seconds}


def main() -> None:
    with SessionLocal() as db:
        values = proofs_waiting(db)
    for key, value in values.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
