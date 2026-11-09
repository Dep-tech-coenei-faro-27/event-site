"""add optional nif to transactions

Revision ID: d2e8a47c1b95
Revises: b8d4f1a6c392
Create Date: 2026-10-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e8a47c1b95"
down_revision: str | None = "b8d4f1a6c392"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A new nullable column: code that does not know it keeps working during the deploy.
    op.add_column("transactions", sa.Column("nif", sa.String(length=9), nullable=True))


def downgrade() -> None:
    # destructive: ok - the NIF is only an optional invoicing detail
    op.drop_column("transactions", "nif")
