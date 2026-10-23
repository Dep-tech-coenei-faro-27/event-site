"""create student proofs

Revision ID: f1a8d3c6e902
Revises: d6b3e9a15c47
Create Date: 2026-10-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a8d3c6e902"
down_revision: str | None = "d6b3e9a15c47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUS = "student_verification_status IN ('pending', 'verified', 'rejected')"
NEW_STATUS = (
    "student_verification_status IN "
    "('pending', 'none', 'submitted', 'verified', 'rejected')"
)


def upgrade() -> None:
    # The new states are only added. Existing rows keep "pending", which the new code
    # reads as "none", so the previous code can keep serving during the deploy.
    # destructive: ok - the constraint is recreated at once, in the same transaction
    op.drop_constraint("ck_users_student_status", "users", type_="check")
    op.create_check_constraint("ck_users_student_status", "users", NEW_STATUS)
    op.alter_column("users", "student_verification_status", server_default="none")

    op.create_table(
        "student_proofs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("file_kind", sa.String(3), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_name", sa.String(64), nullable=True),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "status IN ('submitted', 'verified', 'rejected')",
            name="ck_student_proofs_status",
        ),
        sa.CheckConstraint(
            "file_kind IN ('pdf', 'jpg', 'png')", name="ck_student_proofs_file_kind"
        ),
        sa.CheckConstraint(
            "length(file_hash) = 64", name="ck_student_proofs_file_hash"
        ),
    )
    op.create_index("ix_student_proofs_user_id", "student_proofs", ["user_id"])
    op.create_index("ix_student_proofs_file_hash", "student_proofs", ["file_hash"])
    op.create_index(
        "uq_student_proofs_one_active",
        "student_proofs",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'submitted'"),
    )
    op.create_index(
        "uq_student_proofs_verified_hash",
        "student_proofs",
        ["file_hash"],
        unique=True,
        postgresql_where=sa.text("status = 'verified'"),
    )

    op.create_table(
        "student_proof_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "proof_id",
            sa.Integer(),
            sa.ForeignKey("student_proofs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_student_proof_events_proof_id", "student_proof_events", ["proof_id"]
    )

    op.create_table(
        "institution_nipcs",
        sa.Column("nipc", sa.String(9), primary_key=True),
        sa.Column("institution", sa.String(40), nullable=False),
        sa.Column("registered_by", sa.String(64), nullable=False),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "proof_id",
            sa.Integer(),
            sa.ForeignKey("student_proofs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint("length(nipc) = 9", name="ck_institution_nipcs_nipc"),
    )
    op.create_index(
        "ix_institution_nipcs_institution", "institution_nipcs", ["institution"]
    )


def downgrade() -> None:
    # destructive: ok - the tables are new in this migration
    op.drop_table("institution_nipcs")
    op.drop_table("student_proof_events")
    op.drop_table("student_proofs")
    op.execute(
        "UPDATE users SET student_verification_status = 'pending' "
        "WHERE student_verification_status IN ('none', 'submitted')"
    )
    op.drop_constraint("ck_users_student_status", "users", type_="check")
    op.create_check_constraint("ck_users_student_status", "users", OLD_STATUS)
    op.alter_column("users", "student_verification_status", server_default="pending")
