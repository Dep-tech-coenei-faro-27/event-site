# event-site

## Documentação

- [`docs/deploy.md`](docs/deploy.md): como o site chega ao servidor (GitHub Actions e túnel da Cloudflare), segredos, cron, cópias de segurança, como verificar e reverter um deploy.
- [`docs/api-auth.md`](docs/api-auth.md): contrato dos endpoints de autenticação, para quem faz o frontend.
- [`backend/README.md`](backend/README.md): o backend (configuração, sessões, limites de pedidos, testes).

## Docker

O `docker-compose.yml` arranca a base de dados (`postgres`), a API (`backend`), o site (`frontend`, o nginx que também encaminha `/api`) e o túnel da Cloudflare (`tunnel`).
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

### Em desenvolvimento

O `docker-compose.dev.yml` acrescenta o Mailpit, que apanha os emails que a API envia (verificação e recuperação de password). Os emails aparecem em http://localhost:8025.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file backend/.env up -d --build postgres backend mailpit
```

- A API corre as migrations sozinha ao arrancar (`RUN_MIGRATIONS=false` no `backend/.env` desliga-o).
- O contentor da API corre como um utilizador sem privilégios.
- Para ver o site completo (frontend e API no mesmo endereço), acrescente `frontend` à lista e abra http://localhost:8080.

### Cópias de segurança

Na pasta do projeto:

```bash
scripts/backup.sh                                  # cria backups/db-AAAAMMDD-HHMMSS.dump e media-....tar.gz
scripts/restore.sh backups/db-....dump nome_novo   # restaura para uma base nova (nunca por cima de uma existente)
```

As cópias têm dados pessoais: ficam só legíveis por quem as criou, e não devem ser enviadas para o Git nem partilhadas.
