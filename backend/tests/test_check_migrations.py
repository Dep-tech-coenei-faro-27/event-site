import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_migrations.py"
spec = importlib.util.spec_from_file_location("check_migrations", SCRIPT)
check_migrations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_migrations)


def lines_for(body: str, downgrade: str = "    pass") -> list[tuple[int, str]]:
    source = (
        "import sqlalchemy as sa\n"
        "from alembic import op\n\n\n"
        f"def upgrade() -> None:\n{body}\n\n\n"
        f"def downgrade() -> None:\n{downgrade}\n"
    )
    return check_migrations.violations(source)


def test_adding_tables_columns_and_indexes_is_safe():
    body = (
        '    op.create_table("t", sa.Column("id", sa.Integer()))\n'
        '    op.add_column("t", sa.Column("x", sa.Integer(), nullable=False,'
        ' server_default="0"))\n'
        '    op.create_index("ix_t_x", "t", ["x"])\n'
        '    op.alter_column("t", "x", nullable=True)'
    )

    assert lines_for(body) == []


@pytest.mark.parametrize(
    "operation, reason",
    [
        ('op.drop_column("t", "x")', "remove"),
        ('op.drop_table("t")', "remove"),
        ('op.rename_table("t", "u")', "remove"),
        ('op.alter_column("t", "x", new_column_name="y")', "renomeia"),
        ('op.alter_column("t", "x", type_=sa.String(5))', "tipo"),
        ('op.alter_column("t", "x", nullable=False)', "obrigatória"),
        ('op.execute("DROP TABLE t")', "SQL"),
        ('op.execute("delete from t")', "SQL"),
    ],
)
def test_destructive_operations_are_flagged(operation, reason):
    found = lines_for(f"    {operation}")

    assert len(found) == 1
    assert reason in found[0][1]


def test_the_marker_on_the_line_or_the_one_above_allows_it():
    same_line = '    op.drop_column("t", "x")  # destructive: ok - já não é usada'
    line_above = '    # destructive: ok - já não é usada\n    op.drop_column("t", "x")'

    assert lines_for(same_line) == []
    assert lines_for(line_above) == []


def test_a_marker_far_away_does_not_count():
    body = (
        "    # destructive: ok - isto é de outra operação\n"
        '    op.create_table("t", sa.Column("id", sa.Integer()))\n'
        '    op.drop_column("t", "x")'
    )

    assert len(lines_for(body)) == 1


def test_only_upgrade_is_checked_because_downgrade_is_supposed_to_undo_things():
    downgrade = '    op.drop_column("t", "x")\n    op.drop_table("t")'

    assert (
        lines_for('    op.add_column("t", sa.Column("x", sa.Integer()))', downgrade)
        == []
    )


def test_a_file_without_upgrade_is_ignored():
    assert check_migrations.violations("x = 1\n") == []


def test_the_line_number_points_at_the_operation():
    body = (
        '    op.add_column("t", sa.Column("x", sa.Integer()))\n'
        '    op.drop_column("t", "x")'
    )

    assert lines_for(body)[0][0] == 7


def test_the_migrations_that_already_exist_are_known_to_the_rule():
    versions = SCRIPT.parents[1] / "backend" / "alembic" / "versions"
    flagged = {
        path.name
        for path in versions.glob("*.py")
        if check_migrations.violations(path.read_text(encoding="utf-8"))
    }

    # a única já existente é o alargamento da coluna role (String(5) para String(20)),
    # que é seguro para o código antigo. A regra só olha para as migrations novas de
    # cada PR.
    assert flagged == {"96579782156e_harden_users_table.py"}
