"""merge payment gateway and terms acceptance heads

Revision ID: 720223540bfc
Revises: c7f1a9e2d4b8, da2f4e30cdcd
Create Date: 2026-10-10 22:32:38.500081

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "720223540bfc"
down_revision: str | Sequence[str] | None = ("c7f1a9e2d4b8", "da2f4e30cdcd")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
