"""add geral_refeicoes ticket tier

Revision ID: e5a7c3b91d20
Revises: d2e8a47c1b95
Create Date: 2026-10-20 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a7c3b91d20"
down_revision: str | None = "d2e8a47c1b95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "tier IN ('acesso', 'refeicoes', 'completo', 'geral')"
NEW = "tier IN ('acesso', 'refeicoes', 'completo', 'geral', 'geral_refeicoes')"


def upgrade() -> None:
    # Only the constraint is widened. The row of the new modality is NOT inserted
    # here: the previous code, which keeps serving during the deploy, does not know
    # the value and would fail reading it. `set_price` creates it with the first price.
    # destructive: ok - the constraint is recreated at once, in the same transaction
    op.drop_constraint("ck_ticket_tiers_tier", "ticket_tiers", type_="check")
    op.create_check_constraint("ck_ticket_tiers_tier", "ticket_tiers", NEW)


def downgrade() -> None:
    # destructive: ok - fails (restricted by transactions) if the modality was sold
    op.execute("DELETE FROM ticket_tiers WHERE tier = 'geral_refeicoes'")
    op.drop_constraint("ck_ticket_tiers_tier", "ticket_tiers", type_="check")
    op.create_check_constraint("ck_ticket_tiers_tier", "ticket_tiers", OLD)
