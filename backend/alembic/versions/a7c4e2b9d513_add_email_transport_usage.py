"""add email transport usage

Revision ID: a7c4e2b9d513
Revises: f1a8d3c6e902
Create Date: 2026-10-25 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c4e2b9d513"
down_revision: str | None = "f1a8d3c6e902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_transport_usage",
        sa.Column("transport", sa.String(length=20), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("sent", sa.Integer(), nullable=False),
        sa.Column("exhausted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("transport", "day"),
    )


def downgrade() -> None:
    op.drop_table("email_transport_usage")
