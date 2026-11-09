"""The tax numbers the migration seeds are valid and point at known institutions."""

import importlib.util
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.domains.students.institutions import institution_by_key, is_valid_nipc
from tests.conftest import TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parents[1]
SEED_FILE = (
    BACKEND_DIR
    / "alembic"
    / "versions"
    / "b4e7c1a9d305_seed_known_institution_nipcs.py"
)
BEFORE = "d3f9a1c7b624"
THIS = "b4e7c1a9d305"

spec = importlib.util.spec_from_file_location("seed_known_nipcs", SEED_FILE)
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


def test_every_seeded_nipc_has_a_valid_check_digit_and_a_known_institution():
    for nipc, key in seed.KNOWN_NIPCS:
        assert is_valid_nipc(nipc), nipc
        assert institution_by_key(key) is not None, key


def test_no_nipc_is_seeded_twice_or_for_two_institutions():
    numbers = [nipc for nipc, _ in seed.KNOWN_NIPCS]

    assert len(numbers) == len(set(numbers))


postgres_only = pytest.mark.skipif(
    not (TEST_DATABASE_URL or "").startswith("postgresql"),
    reason="the migrations are written for PostgreSQL",
)


@pytest.fixture
def scratch_database():
    server = make_url(TEST_DATABASE_URL)
    name = f"seed_{uuid.uuid4().hex[:12]}"
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = server.set(database=name)
    engine = create_engine(url)
    yield url, engine
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()


def alembic(url, *arguments):
    env = {
        **os.environ,
        "POSTGRES_USER": url.username,
        "POSTGRES_PASSWORD": url.password,
        "POSTGRES_HOST": url.host,
        "POSTGRES_PORT": str(url.port),
        "POSTGRES_DB": url.database,
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]


def stored(engine):
    with engine.connect() as conn:
        return {
            row[0]: (row[1], row[2])
            for row in conn.execute(
                text("SELECT nipc, institution, registered_by FROM institution_nipcs")
            )
        }


@postgres_only
def test_the_migration_seeds_the_known_nipcs(scratch_database):
    url, engine = scratch_database

    alembic(url, "upgrade", "head")

    rows = stored(engine)
    for nipc, key in seed.KNOWN_NIPCS:
        assert rows[nipc] == (key, seed.SEEDED_BY)


@postgres_only
def test_the_migration_keeps_what_a_reviewer_already_registered(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", BEFORE)
    nipc = seed.KNOWN_NIPCS[0][0]
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO institution_nipcs (nipc, institution, registered_by)"
                " VALUES (:nipc, 'UCOIMBRA', 'revisor')"
            ),
            {"nipc": nipc},
        )

    alembic(url, "upgrade", THIS)

    assert stored(engine)[nipc] == ("UCOIMBRA", "revisor")
    assert len(stored(engine)) == len(seed.KNOWN_NIPCS)
