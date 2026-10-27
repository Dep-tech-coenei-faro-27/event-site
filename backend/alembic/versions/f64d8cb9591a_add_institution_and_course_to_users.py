"""add institution and course to users

Revision ID: f64d8cb9591a
Revises: da2f4e30cdcd
Create Date: 2026-10-12 23:07:02.470347

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.domains.users.enums import PortugueseInstitution

# Os cursos de então, congelados aqui: o enum `Course` deixou de existir (a coluna
# foi retirada na migração `b7c4e1a92d35`) e uma migração não deve depender do
# código da aplicação.
COURSES = (
    "Engenharia Informática",
    "Medicina",
    "Direito",
    "Economia",
    "Gestão",
    "Design",
    "Engenharia Eletrotécnica e de Computadores",
    "Engenharia Mecânica",
    "Engenharia Civil",
    "Engenharia Química",
    "Engenharia Biomédica",
    "Engenharia Aeroespacial",
    "Engenharia Física",
    "Engenharia do Ambiente",
    "Engenharia e Gestão Industrial",
    "Ciência de Computadores",
    "Ciência de Dados",
    "Enfermagem",
    "Medicina Dentária",
    "Medicina Veterinária",
    "Ciências Farmacêuticas",
    "Fisioterapia",
    "Ciências da Nutrição",
    "Psicologia",
    "Biologia",
    "Bioquímica",
    "Ciências Biomédicas",
    "Matemática",
    "Matemática Aplicada",
    "Física",
    "Química",
    "Geologia",
    "Contabilidade",
    "Finanças",
    "Marketing",
    "Gestão de Recursos Humanos",
    "Administração Pública",
    "Relações Internacionais",
    "Ciência Política",
    "Ciências da Comunicação",
    "Sociologia",
    "Serviço Social",
    "História",
    "Filosofia",
    "Línguas e Literaturas",
    "Tradução",
    "Arquitetura",
    "Artes Plásticas",
    "Design Gráfico",
    "Tecnologias Multimédia",
    "Cinema e Artes Audiovisuais",
    "Teatro e Artes Performativas",
    "Música",
    "Turismo",
    "Gestão Hoteleira",
    "Ciências do Desporto",
    "Educação Básica",
)

# revision identifiers, used by Alembic.
revision: str = "f64d8cb9591a"
down_revision: str | None = "da2f4e30cdcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "institution",
            sa.Enum(
                *[e.value for e in PortugueseInstitution],
                name="ck_users_institution",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "course",
            sa.Enum(
                *COURSES,
                name="ck_users_course",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "course")
    op.drop_column("users", "institution")
