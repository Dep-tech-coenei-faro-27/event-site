from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_the_migration_graph_has_a_single_head():
    """Two heads mean two parallel branches were merged without a merge revision.

    ``alembic upgrade head`` fails on multiple heads, so the deploy would break.
    Every merge that brings a migration from another branch must add a merge
    revision (or re-chain it) until only one head remains.
    """
    script = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini")))
    heads = script.get_heads()

    assert len(heads) == 1, f"expected a single migration head, found: {heads}"
