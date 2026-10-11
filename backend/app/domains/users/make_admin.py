import argparse
import sys

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domains.users.models import Role
from app.domains.users.service import get_user_by_email


def promote_to_admin(db: Session, email: str) -> int:
    user = get_user_by_email(db, email)
    if not user:
        print(f"User with email {email} not found.")
        return 1
    if not user.is_verified:
        print(f"User with email {email} is not verified.")
        return 1
    if user.role == Role.ADMIN:
        print(f"User with email {email} is already an admin.")
        return 1

    user.role = Role.ADMIN
    db.commit()
    print(f"User with email {email} promoted to admin.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a user to admin")
    parser.add_argument("email", help="Email of the user to promote")
    args = parser.parse_args()
    with SessionLocal() as db:
        sys.exit(promote_to_admin(db, args.email))


if __name__ == "__main__":
    main()
