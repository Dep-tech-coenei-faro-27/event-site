"""add ticket tier to tickets

Revision ID: c2e8a4f71b39
Revises: a3d5f8b2c916
Create Date: 2026-10-18 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2e8a4f71b39"
down_revision: str | None = "a3d5f8b2c916"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A value and not a foreign key: inserting a ticket must not lock the modality
    # row that a late payment locks to check the stock (it deadlocked).
    op.add_column(
        "tickets",
        sa.Column(
            "ticket_tier",
            sa.Enum(
                "acesso",
                "refeicoes",
                "completo",
                "geral",
                "geral_refeicoes",
                name="ck_tickets_ticket_tier",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=True,
        ),
    )
    # Tickets issued before this column take the modality of their transaction.
    op.execute(
        """
        UPDATE tickets
        SET ticket_tier = (
            SELECT ticket_tiers.tier
            FROM transactions
            JOIN ticket_tiers ON ticket_tiers.id = transactions.ticket_tier_id
            WHERE transactions.reference = tickets.transaction_reference
        )
        WHERE ticket_tier IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_tickets_ticket_tier", "tickets", type_="check")
    op.drop_column("tickets", "ticket_tier")
