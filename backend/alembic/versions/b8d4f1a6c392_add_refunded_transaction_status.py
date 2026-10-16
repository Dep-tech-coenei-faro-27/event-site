"""add refunded transaction status

Revision ID: b8d4f1a6c392
Revises: a3c9e5b71f24
Create Date: 2026-10-16 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d4f1a6c392"
down_revision: str | None = "a3c9e5b71f24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "status IN ('pending', 'confirmed', 'failed', 'expired', 'refund_due')"
NEW = (
    "status IN ('pending', 'confirmed', 'failed', 'expired', 'refund_due', 'refunded')"
)


def upgrade() -> None:
    # The new constraint is wider (adds a value) and both steps run in one transaction
    # destructive: ok - recreated at once, the old code never sees a table without it
    op.drop_constraint("ck_transactions_status", "transactions", type_="check")
    op.create_check_constraint("ck_transactions_status", "transactions", NEW)


def downgrade() -> None:
    # The old schema has no "refunded": it is closest to expired, which holds no seat.
    op.execute("UPDATE transactions SET status = 'expired' WHERE status = 'refunded'")
    # destructive: ok - the constraint is recreated at once, in the same transaction
    op.drop_constraint("ck_transactions_status", "transactions", type_="check")
    op.create_check_constraint("ck_transactions_status", "transactions", OLD)
