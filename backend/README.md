# event-site-backend

Backend da API do event-site, construído com **FastAPI**, **SQLAlchemy 2** e **PostgreSQL**, gerido com **uv**.

## Estrutura

```
backend/
├── app/
│   ├── core/          # Configuração e settings
│   ├── db/            # Sessão e base do SQLAlchemy
│   └── domains/       # Separação por domínio
│       └── health/    # router.py, schemas.py, models.py, service.py
├── alembic/           # Migrations
└── pyproject.toml
```

Cada domínio tem os seus próprios ficheiros (`router.py`, `schemas.py`, `models.py`, `service.py`). Para criar um novo domínio, copie a estrutura de `app/domains/health/`.

## Testes

Os testes correm, por omissão, contra uma **base de dados em memória (SQLite)**
sem qualquer configuração extra:

```bash
cp .env.example .env
uv sync --dev
make test
```

Para testar contra um PostgreSQL real (como no CI), defina `TEST_DATABASE_URL`:

```bash
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/event_site_test make test
```

O CI executa a suite contra PostgreSQL (ver `.github/workflows/ci.yml`), o que
garante compatibilidade com a base em produção.

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