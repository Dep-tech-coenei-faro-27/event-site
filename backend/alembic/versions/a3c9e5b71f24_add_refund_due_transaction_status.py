"""add refund_due transaction status

Revision ID: a3c9e5b71f24
Revises: e4b7c1d92a60
Create Date: 2026-10-16 15:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c9e5b71f24"
down_revision: str | None = "e4b7c1d92a60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "status IN ('pending', 'confirmed', 'failed', 'expired')"
NEW = "status IN ('pending', 'confirmed', 'failed', 'expired', 'refund_due')"


def upgrade() -> None:
    # The new constraint is wider (adds a value) and both steps run in one transaction
    # destructive: ok - recreated at once, the old code never sees a table without it
    op.drop_constraint("ck_transactions_status", "transactions", type_="check")
    op.create_check_constraint("ck_transactions_status", "transactions", NEW)


def downgrade() -> None:
    # A payment waiting for a refund was paid: it goes back to confirmed.
    op.execute(
        "UPDATE transactions SET status = 'confirmed' WHERE status = 'refund_due'"
    )
    op.drop_constraint("ck_transactions_status", "transactions", type_="check")
    op.create_check_constraint("ck_transactions_status", "transactions", OLD)
