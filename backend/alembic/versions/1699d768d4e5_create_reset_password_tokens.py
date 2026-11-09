"""create reset password tokens

Revision ID: 1699d768d4e5
Revises: b4e7a2c91d05
Create Date: 2026-10-04 18:08:53.770961

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1699d768d4e5"
down_revision: str | None = "b4e7a2c91d05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reset_password_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reset_password_tokens_jti"),
        "reset_password_tokens",
        ["jti"],
        unique=True,
    )
    op.create_index(
        op.f("ix_reset_password_tokens_user_id"),
        "reset_password_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_reset_password_tokens_user_id"), table_name="reset_password_tokens"
    )
    op.drop_index(
        op.f("ix_reset_password_tokens_jti"), table_name="reset_password_tokens"
    )
    op.drop_table("reset_password_tokens")
