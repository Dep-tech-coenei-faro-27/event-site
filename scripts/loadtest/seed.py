"""Prepare a load-test database: verified accounts and the ticket office open.

Run from ``backend/`` with the backend's environment pointing at the load-test
database (``run.sh`` does it):

    POSTGRES_DB=loadtest_x .venv/bin/python ../scripts/loadtest/seed.py --users 300

It refuses any database whose name does not start with ``loadtest``, so it can
never write accounts into the real database by mistake. Every account has the
same password and an address under ``loadtest.example.com`` (a reserved domain); the
load tests run without SMTP, so no email leaves the machine anyway.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import delete, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domains.payments.models import TicketTier  # noqa: E402
from app.domains.payments.set_price import set_price  # noqa: E402
from app.domains.users.models import User  # noqa: E402

EMAIL_PATTERN = "load-{:04d}@loadtest.example.com"
PASSWORD = "LoadTest-2027!"
DB_PREFIX = "loadtest"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--users", type=int, default=300)
    parser.add_argument("--price-cents", type=int, default=3500)
    args = parser.parse_args(argv)

    if not settings.POSTGRES_DB.startswith(DB_PREFIX):
        sys.exit(
            f"refusing to seed {settings.POSTGRES_DB!r}: the load-test database "
            f"name must start with {DB_PREFIX!r}"
        )

    password_hash = hash_password(PASSWORD)
    emails = [EMAIL_PATTERN.format(i) for i in range(args.users)]
    with SessionLocal() as db:
        db.execute(delete(User).where(User.email.like("load-%@loadtest.example.com")))
        db.add_all(
            User(
                name=f"Carga {i:04d}",
                email=email,
                password_hash=password_hash,
                is_verified=True,
            )
            for i, email in enumerate(emails)
        )
        db.commit()
        set_price(db, TicketTier.GERAL, args.price_cents)
        count = db.scalar(select(User.id).where(User.email == emails[-1]).limit(1))
    print(f"seeded {args.users} accounts (last id {count}); geral open")


if __name__ == "__main__":
    main()
