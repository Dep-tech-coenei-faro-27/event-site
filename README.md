# event-site

## Docker

O `docker-compose.yml` arranca a base de dados (`postgres`), a API (`backend`) e o túnel da Cloudflare (`tunnel`).
Cada serviço só recebe as variáveis de que precisa, por isso o compose lê o `backend/.env` com `--env-file`.

```bash
cp backend/.env.example backend/.env
docker compose --env-file backend/.env up -d --build postgres backend
```

Para não escrever a opção de cada vez:

```bash
export COMPOSE_ENV_FILES=backend/.env      # PowerShell: $env:COMPOSE_ENV_FILES = "backend/.env"
docker compose up -d --build postgres backend
```

Sem isto o compose pára com a mensagem `Corra docker compose --env-file backend/.env`.

- O Postgres e a API só ficam acessíveis a partir da própria máquina (`127.0.0.1`).
- O `tunnel` não é preciso em desenvolvimento. No servidor, o token vem do ficheiro `tunnel.env`, que o workflow de deploy escreve com permissões 600.
- Os segredos do deploy (`POSTGRES_*`, `JWT_SECRET_KEY`, `TUNNEL_TOKEN`, ...) estão nos Secrets do repositório e nunca vão para o Git.
