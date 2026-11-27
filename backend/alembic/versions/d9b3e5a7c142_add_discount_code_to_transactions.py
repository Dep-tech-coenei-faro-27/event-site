"""add the discount code to transactions

O código de desconto usado numa compra (se houver). O valor da transação já é o preço
depois do desconto; a coluna só diz de onde veio. É nula nas compras que já existem.

Revision ID: d9b3e5a7c142
Revises: c7d2a4e8b516
Create Date: 2026-11-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9b3e5a7c142"
down_revision: str | None = "c7d2a4e8b516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("discount_code", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    # destructive: ok - only says where a discount came from; the amount paid stays
    op.drop_column("transactions", "discount_code")
