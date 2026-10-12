from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PortugueseInstitution(str, Enum):
    ULISBOA = "Universidade de Lisboa"
    UPORTO = "Universidade do Porto"
    UCOIMBRA = "Universidade de Coimbra"
    UNL = "Universidade Nova de Lisboa"
    UMINHO = "Universidade do Minho"
    UA = "Universidade de Aveiro"
    ISCTE = "ISCTE - Instituto Universitário de Lisboa"
    UBI = "Universidade da Beira Interior"
    UCA = "Universidade Católica Portuguesa"
    # Adiciona outras opções conforme necessário


class Course(str, Enum):
    ENGENHARIA_INFORMATICA = "Engenharia Informática"
    MEDICINA = "Medicina"
    DIREITO = "Direito"
    ECONOMIA = "Economia"
    GESTAO = "Gestão"
    DESIGN = "Design"
    # Adiciona outros cursos conforme necessário


class Role(Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_users_name_not_blank"),
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_blank"),
        CheckConstraint(
            "length(password_hash) > 0", name="ck_users_password_hash_not_empty"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        SAEnum(
            Role,
            name="ck_users_role",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=Role.USER,
        server_default=Role.USER.name,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="false",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        server_default="0",
    )
    terms_accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    term_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=False,
        server_default="'1.0'",
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    institution: Mapped[PortugueseInstitution | None] = mapped_column(
        SAEnum(
            PortugueseInstitution,
            name="ck_users_institution",
            native_enum=False,
            create_constraint=True
        ),
        nullable=True
    )
    course: Mapped[Course | None] = mapped_column(
        SAEnum(
            Course,
            name="ck_users_course",
            native_enum=False,
            create_constraint=True
        ),
        nullable=True
    )


Index("uq_users_email_lower", func.lower(User.email), unique=True)
