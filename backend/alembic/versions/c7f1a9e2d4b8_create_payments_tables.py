"""create tickets and transactions, add student verification to users

Revision ID: c7f1a9e2d4b8
Revises: 832692a10dc1
Create Date: 2026-10-09 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7f1a9e2d4b8"
down_revision: str | None = "832692a10dc1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TIER_ROWS = [
    ("acesso", "Apenas acesso", True, "TICKET_PRICE_ACESSO_CENTS"),
    ("refeicoes", "Acesso + refeições", True, "TICKET_PRICE_REFEICOES_CENTS"),
    ("completo", "Experiência completa", True, "TICKET_PRICE_COMPLETO_CENTS"),
    ("geral", "Passe geral", False, "TICKET_PRICE_GERAL_CENTS"),
]


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "student_verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "student_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_users_student_status",
        "users",
        "student_verification_status IN ('pending', 'verified', 'rejected')",
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "is_student",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("inventory_limit", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("price_cents >= 0", name="ck_tickets_price_not_negative"),
        sa.CheckConstraint(
            "inventory_limit IS NULL OR inventory_limit >= 0",
            name="ck_tickets_inventory_not_negative",
        ),
        sa.CheckConstraint(
            "tier IN ('acesso', 'refeicoes', 'completo', 'geral')",
            name="ck_tickets_tier",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_tier"), "tickets", ["tier"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=15), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_reference", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'failed', 'expired')",
            name="ck_transactions_status",
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transactions_reference"),
        "transactions",
        ["reference"],
        unique=True,
    )
    op.create_index(op.f("ix_transactions_user_id"), "transactions", ["user_id"])
    op.create_index(op.f("ix_transactions_ticket_id"), "transactions", ["ticket_id"])
    op.create_index(op.f("ix_transactions_status"), "transactions", ["status"])

    _seed_tickets()


def _seed_tickets() -> None:
    from app.core.config import settings

    tickets = sa.table(
        "tickets",
        sa.column("tier", sa.String),
        sa.column("name", sa.String),
        sa.column("price_cents", sa.Integer),
        sa.column("is_student", sa.Boolean),
        sa.column("inventory_limit", sa.Integer),
    )
    op.bulk_insert(
        tickets,
        [
            {
                "tier": tier,
                "name": name,
                "price_cents": int(getattr(settings, setting)),
                "is_student": is_student,
                "inventory_limit": None,
            }
            for tier, name, is_student, setting in TIER_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_status"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_ticket_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_reference"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_tickets_tier"), table_name="tickets")
    op.drop_table("tickets")
    op.drop_constraint("ck_users_student_status", "users", type_="check")
    op.drop_column("users", "student_verified_at")
    op.drop_column("users", "student_verification_status")
