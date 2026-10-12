"""add institution and course to users

Revision ID: f64d8cb9591a
Revises: da2f4e30cdcd
Create Date: 2026-10-12 23:07:02.470347

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.domains.users.enums import Course, PortugueseInstitution

# revision identifiers, used by Alembic.
revision: str = "f64d8cb9591a"
down_revision: str | None = "da2f4e30cdcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "institution",
            sa.Enum(
                *[e.value for e in PortugueseInstitution],
                name="ck_users_institution",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "course",
            sa.Enum(
                *[e.value for e in Course],
                name="ck_users_course",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "course")
    op.drop_column("users", "institution")
