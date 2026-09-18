SHELL := /bin/bash
PYTHON := .venv/bin/python
UV := uv
VENV := .venv
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: help install sync dev run test lint format db-upgrade db-downgrade db-revision deploy

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Instala todas as dependências (incluindo dev)
	$(UV) sync --dev

sync: ## Sincroniza o ambiente com o lockfile
	$(UV) sync

dev: ## Corre o servidor em modo desenvolvimento (hot reload)
	$(VENV)/bin/uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

run: ## Corre o servidor em modo produção local
	$(VENV)/bin/uvicorn app.main:app --host $(HOST) --port $(PORT)

test: ## Corre os testes
	$(VENV)/bin/pytest

lint: ## Verifica o estilo do código
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

format: ## Formata o código
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .

db-upgrade: ## Aplica as migrations pendentes (upgrade head)
	$(VENV)/bin/alembic upgrade head

db-downgrade: ## Desce uma migration
	$(VENV)/bin/alembic downgrade -1

db-revision: ## Cria uma nova migration autogerada (uso: make db-revision m="descrição")
	$(VENV)/bin/alembic revision --autogenerate -m "$(m)"

deploy: ## Faz deploy da aplicação em produção
	$(VENV)/bin/alembic upgrade head
	$(VENV)/bin/uvicorn app.main:app --host $(HOST) --port $(PORT) --workers 4