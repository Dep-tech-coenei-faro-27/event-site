"""add the shirt size to transactions and tickets

The students who buy a ticket get a shirt and give its size (XS to XXL, unisex) at
checkout. It is kept on the payment and passes to the ticket when the payment is
confirmed. Both columns are null on what already exists: those students are asked by
email and answer on the account page.

Revision ID: e8c4a6d2b731
Revises: d9b3e5a7c142
Create Date: 2026-11-28 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8c4a6d2b731"
down_revision: str | None = "d9b3e5a7c142"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _shirt_size(name: str) -> sa.Enum:
    return sa.Enum(
        "XS",
        "S",
        "M",
        "L",
        "XL",
        "XXL",
        name=name,
        native_enum=False,
        create_constraint=True,
        length=3,
    )


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "shirt_size", _shirt_size("ck_transactions_shirt_size"), nullable=True
        ),
    )
    op.add_column(
        "tickets",
        sa.Column("shirt_size", _shirt_size("ck_tickets_shirt_size"), nullable=True),
    )


def downgrade() -> None:
    # destructive: ok - only the size of the shirt, which can be asked for again
    op.drop_constraint("ck_tickets_shirt_size", "tickets", type_="check")
    op.drop_column("tickets", "shirt_size")
    # destructive: ok - only the size of the shirt, which can be asked for again
    op.drop_constraint("ck_transactions_shirt_size", "transactions", type_="check")
    op.drop_column("transactions", "shirt_size")
