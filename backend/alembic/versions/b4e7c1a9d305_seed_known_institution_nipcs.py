"""seed the tax numbers of institutions whose seals were seen on real proofs

Um comprovativo só é aprovado sem pessoa se o NIPC do selo que o assina já estiver em
``institution_nipcs`` (a tabela aprende-se ao aprovar à mão o primeiro comprovativo de
cada instituição). Sem isto, o primeiro estudante de cada universidade fica sempre na
fila de revisão. Aqui entram só os NIPC de selos eletrónicos qualificados vistos em
comprovativos reais, cada um ligado à sua universidade. As linhas já existentes não
se tocam.

Revision ID: b4e7c1a9d305
Revises: d3f9a1c7b624
Create Date: 2026-11-09 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e7c1a9d305"
down_revision: str | None = "d3f9a1c7b624"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED_BY = "seed"

# (NIPC, chave de ``PortugueseInstitution``)
KNOWN_NIPCS: tuple[tuple[str, str], ...] = (
    ("501413197", "UPORTO"),  # Universidade do Porto
    ("505387271", "UALG"),  # Universidade do Algarve
    ("501559094", "UNL"),  # Universidade Nova de Lisboa (selo da NOVA IMS)
    ("501461108", "UA"),  # Universidade de Aveiro
)


def upgrade() -> None:
    table = sa.table(
        "institution_nipcs",
        sa.column("nipc", sa.String),
        sa.column("institution", sa.String),
        sa.column("registered_by", sa.String),
    )
    bind = op.get_bind()
    for nipc, institution in KNOWN_NIPCS:
        already = bind.execute(
            sa.select(table.c.nipc).where(table.c.nipc == nipc)
        ).first()
        if already is None:
            bind.execute(
                sa.insert(table).values(
                    nipc=nipc, institution=institution, registered_by=SEEDED_BY
                )
            )


def downgrade() -> None:
    # Os NIPC semeados ficam: são inofensivos sozinhos e quem os aprovou à mão depois
    # também os usa; apagá-los não desfaz nada que valha a pena.
    pass
