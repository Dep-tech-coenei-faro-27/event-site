"""add text body to email outbox

Revision ID: d6b3e9a15c47
Revises: c2e8a4f71b39
Create Date: 2026-10-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6b3e9a15c47"
down_revision: str | None = "c2e8a4f71b39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("email_outbox", sa.Column("text_body", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("email_outbox", "text_body")
