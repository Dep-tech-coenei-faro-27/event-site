"""add phone to users

Contacto opcional da conta (Dados pessoais). Texto de 20 caracteres no máximo, sem
restrição: a validação (9 a 15 dígitos, com ou sem +) está na API.

Revision ID: c5d9a3e7f1b8
Revises: b7c4e1a92d35
Create Date: 2026-10-25 20:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d9a3e7f1b8"
down_revision: str | None = "b7c4e1a92d35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    # destructive: ok - volta ao estado anterior; o contacto guardado perde-se
    op.drop_column("users", "phone")
