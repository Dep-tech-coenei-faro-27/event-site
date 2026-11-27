"""add the invoice address to transactions

A compra com NIF leva também a morada, que a fatura com contribuinte exige. As três
colunas são nulas: as compras que já existem ficam como estão (a morada delas pede-se
a quem as fez), e quem compra sem NIF não deixa morada.

Revision ID: c7d2a4e8b516
Revises: b4e7c1a9d305
Create Date: 2026-11-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d2a4e8b516"
down_revision: str | None = "b4e7c1a9d305"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("billing_street", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("billing_postal_code", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "transactions", sa.Column("billing_city", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    # destructive: ok - the address is only kept for the invoice and can be asked again
    op.drop_column("transactions", "billing_city")
    op.drop_column("transactions", "billing_postal_code")
    op.drop_column("transactions", "billing_street")
