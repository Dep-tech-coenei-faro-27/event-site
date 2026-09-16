# event-site-backend

Backend da API do event-site, construído com **FastAPI**, **SQLAlchemy 2** e **PostgreSQL**, gerido com **uv**.

## Estrutura

```
backend/
├── app/
│   ├── core/          # Configuração e settings
│   ├── db/            # Sessão e base do SQLAlchemy
│   └── domains/       # Separação por domínio
│       └── health/    # router.py, schemas.py, models.py, services.py
├── alembic/           # Migrations
└── pyproject.toml
```

Cada domínio tem os seus próprios ficheiros (`router.py`, `schemas.py`, `models.py`, `services.py`). Para criar um novo domínio, copie a estrutura de `app/domains/health/`.

## Setup

```bash
cp .env.example .env
uv sync --dev
uvicorn app.main:app --reload
```

## Comandos úteis

```bash
make dev          # arranca o servidor em modo desenvolvimento
make test         # corre os testes
make lint         # ruff check + format
make format       # ruff format
make db-migrate   # aplica migrations
make db-revise    # cria nova migration
make help         # lista todos os comandos
```