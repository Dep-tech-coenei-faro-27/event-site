"""merge payment gateway and users profile heads

Revision ID: b1f4c9e2a7d3
Revises: 720223540bfc, f64d8cb9591a
Create Date: 2026-10-13 09:00:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b1f4c9e2a7d3"
down_revision: str | Sequence[str] | None = ("720223540bfc", "f64d8cb9591a")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
