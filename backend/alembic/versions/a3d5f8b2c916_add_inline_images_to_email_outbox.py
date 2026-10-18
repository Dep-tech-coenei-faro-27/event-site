"""add inline images to email outbox

Revision ID: a3d5f8b2c916
Revises: e4b7c1d92a60
Create Date: 2026-10-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d5f8b2c916"
down_revision: str | None = "e4b7c1d92a60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("email_outbox", sa.Column("inline_images", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("email_outbox", "inline_images")
