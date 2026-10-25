"""drop institution and course from users

A conta deixa de guardar a instituição e o curso (decisão de 25/10/2026): o site nunca
os pedia ao registar, e o comprovativo de estudante reconhece a instituição pela
assinatura. As listas fechadas deixam de existir.

Revision ID: b7c4e1a92d35
Revises: f1a8d3c6e902
Create Date: 2026-10-25 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c4e1a92d35"
down_revision: str | None = "f1a8d3c6e902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Apagar a coluna leva consigo a restrição CHECK (ck_users_*).
    # destructive: ok - a conta deixou de guardar o curso (nunca se pedia ao registar)
    op.drop_column("users", "course")
    # destructive: ok - a conta deixou de guardar a instituição (idem)
    op.drop_column("users", "institution")


def downgrade() -> None:
    # Voltam as colunas, vazias e sem as listas fechadas (os dados não se recuperam).
    op.add_column(
        "users", sa.Column("institution", sa.String(length=255), nullable=True)
    )
    op.add_column("users", sa.Column("course", sa.String(length=255), nullable=True))
