"""add email outbox

Revision ID: e4b7c1d92a60
Revises: 0999f73061f9
Create Date: 2026-10-15 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4b7c1d92a60"
down_revision: str | None = "0999f73061f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("to_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')", name="ck_email_outbox_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(
        op.f("ix_email_outbox_next_attempt_at"),
        "email_outbox",
        ["next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_outbox_status"), "email_outbox", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_email_outbox_status"), table_name="email_outbox")
    op.drop_index(op.f("ix_email_outbox_next_attempt_at"), table_name="email_outbox")
    op.drop_table("email_outbox")
