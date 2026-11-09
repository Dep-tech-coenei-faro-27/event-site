"""add users check constraints

Revision ID: b4e7a2c91d05
Revises: 96579782156e
Create Date: 2026-10-04 20:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e7a2c91d05"
down_revision: str | None = "96579782156e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_name_not_blank", "users", "length(trim(name)) > 0"
    )
    op.create_check_constraint(
        "ck_users_email_not_blank", "users", "length(trim(email)) > 0"
    )
    op.create_check_constraint(
        "ck_users_password_hash_not_empty", "users", "length(password_hash) > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_password_hash_not_empty", "users", type_="check")
    op.drop_constraint("ck_users_email_not_blank", "users", type_="check")
    op.drop_constraint("ck_users_name_not_blank", "users", type_="check")
