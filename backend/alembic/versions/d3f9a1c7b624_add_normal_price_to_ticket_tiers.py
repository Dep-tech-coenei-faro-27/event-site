"""add normal_price_cents to ticket_tiers

O preço normal de uma modalidade, só enquanto o preço em vigor é um Early Bird: a
página de bilhetes mostra-o riscado ao lado do preço. Quem cobra continua a ser
``price_cents``. Vazio por omissão (nenhuma modalidade fica com Early Bird até se
pôr com ``set_price --normal``).

Revision ID: d3f9a1c7b624
Revises: c5d9a3e7f1b8
Create Date: 2026-10-31 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f9a1c7b624"
down_revision: str | None = "c5d9a3e7f1b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ticket_tiers", sa.Column("normal_price_cents", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        "ck_ticket_tiers_normal_price_above_price",
        "ticket_tiers",
        "normal_price_cents IS NULL"
        " OR (price_cents IS NOT NULL AND normal_price_cents > price_cents)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ticket_tiers_normal_price_above_price", "ticket_tiers", type_="check"
    )
    # destructive: ok - só guardava o preço normal para o mostrar riscado
    op.drop_column("ticket_tiers", "normal_price_cents")
