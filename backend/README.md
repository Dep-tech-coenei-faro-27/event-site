# event-site-backend

Backend da API do event-site, construído com **FastAPI**, **SQLAlchemy 2** e **PostgreSQL**, gerido com **uv**.

Para quem desenvolve o frontend, o contrato dos endpoints está em [`docs/api-auth.md`](../docs/api-auth.md) e [`docs/api-payments.md`](../docs/api-payments.md). Para pôr no ar e operar o servidor, ver [`docs/deploy.md`](../docs/deploy.md).

## Estrutura

```
backend/
├── app/
│   ├── core/          # Configuração, segurança, email e limites de pedidos
│   ├── db/            # Sessão e base do SQLAlchemy
│   └── domains/       # Separação por domínio
│       ├── auth/      # registo, login, verificação de email, recuperação de password
│       ├── health/    # router.py, schemas.py, models.py, service.py
│       ├── payments/  # bilhetes, transações e gateway MB WAY
│       └── users/
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

O CI executa a suite contra PostgreSQL (ver `.github/workflows/ci-backend.yml`), o que
garante compatibilidade com a base em produção.

## Docker

A API e o PostgreSQL correm com o Docker Compose, a partir da raiz do repositório (o README da raiz tem os detalhes):

```bash
cp backend/.env.example backend/.env
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file backend/.env up -d --build postgres backend mailpit
```

- As migrations são aplicadas sozinhas no arranque (`RUN_MIGRATIONS=false` desliga).
- O `docker-compose.dev.yml` junta o Mailpit, uma caixa de email local em http://localhost:8025. Registe um utilizador, abra o email de verificação aí e verifique a conta.
- O PostgreSQL só fica acessível a partir da própria máquina. Se a porta 5432 estiver ocupada, defina `POSTGRES_HOST_PORT` num `.env` na raiz do repositório.
- Atrás de um proxy fora do Docker, defina `FORWARDED_ALLOW_IPS` com o IP do proxy (ver `docs/deploy.md`).

## Setup

```bash
cp .env.example .env
uv sync --dev
uvicorn app.main:app --reload
```

## Configuração

O ficheiro `.env` (ver `.env.example`) define a configuração. Os pontos a ter em conta:

- `JWT_SECRET_KEY` é obrigatória e não tem valor por omissão. Gere uma com `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `ENVIRONMENT` é `dev` ou `prod`, e **por omissão é `prod`**. Em `prod` o arranque falha se faltar alguma destas condições: segredo com pelo menos 32 caracteres, `DEBUG=false`, SMTP configurado, URLs `https` e uma `POSTGRES_PASSWORD` diferente de `postgres`. Para desenvolver, escreva `ENVIRONMENT=dev` no `.env` (o `.env.example` já o faz). Em `prod`, `/docs`, `/redoc` e `/openapi.json` não existem.
- `FRONTEND_VERIFY_PATH` e `FRONTEND_RESET_PATH` são os caminhos do frontend usados nos links dos emails (por omissão `/conta/verificar` e `/conta/redefinir`, os do design).
- `MAX_REQUEST_BYTES` (por omissão 1 MB) é o tamanho máximo do corpo de um pedido. Acima disso a API responde `413`.
- `CORS_ALLOW_ORIGINS` aceita uma lista JSON ou texto separado por vírgulas. Nunca aceita `*` nem `null`, e em `prod` todas as origens têm de ser `https`.
- Sem `SMTP_HOST` os emails não são enviados: ficam no log do servidor, com os links. Chega para testar o registo e a verificação sem servidor de email.
- `SMTP_SECURITY` (`auto`, `starttls`, `ssl`, `none`): com `auto`, a porta 465 usa TLS direto e as outras usam STARTTLS. O certificado do servidor SMTP é sempre verificado. `none` só é permitido em `dev`, para um servidor de email local.
- `MEDIA_DIR` define a pasta servida em `/media` (por omissão `media/`). Só são servidas imagens (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.avif`).

## Sessões

O login devolve o cookie `__Host-access_token` (`HttpOnly`, `Secure`, `SameSite=Lax`, sem `Domain`). O token tem o `id` do utilizador em `sub`, um `jti` (identificador do token) e `tv` (a versão dos tokens do utilizador). Por isso uma sessão pode ser terminada antes de expirar:

- **Logout:** o `jti` do token fica numa lista de tokens revogados até ele expirar.
- **Mudar ou repor a password:** aumenta o `token_version` do utilizador, o que fecha todas as outras sessões. Ao mudar a password, a sessão atual continua com um cookie novo, com o tempo que restava (no mínimo 1 minuto). Repor a password não inicia sessão, e verifica a conta se ainda não estava verificada (o link chegou ao email dela).
- Um token com a versão antiga, ou cujo `jti` foi revogado, recebe `401` (`Token has been revoked.`).

O comando de limpeza apaga também os tokens revogados que já expiraram.

## Limites de pedidos

Os endpoints sensíveis têm limites guardados na base de dados (tabela `rate_limits`), partilhados por todos os workers, em janelas fixas:

| Endpoint | Limite |
| --- | --- |
| `POST /auth/login` | 5 por minuto por email e IP, 20 por minuto por email (de qualquer IP) e 30 por minuto por IP |
| `POST /auth/register` | 2 por minuto por IP |
| `POST /auth/resend-verification-email` | 1 por minuto e 5 por hora por email, e 10 por minuto por IP |
| `POST /auth/forgot-password` | 1 por minuto e 5 por hora por email, e 10 por minuto por IP |
| `PUT /auth/password` | 2 por 15 minutos por utilizador |
| `POST /auth/verify-email` e `POST /auth/reset-password` | 20 por minuto por IP |
| `POST /payment/initiate` | 10 por minuto por utilizador |

O limite de login conta o par email e IP, por isso alguém que falhe a password de outra pessoa não a bloqueia: só se bloqueia a si próprio.

Ao exceder o limite a API devolve `429` com o cabeçalho `Retry-After`. Os valores mudam com as variáveis `RATE_LIMIT_*` do `.env` e `RATE_LIMIT_ENABLED=false` desliga os limites (útil em testes de carga). Atrás de um proxy o IP vem de `X-Forwarded-For`, por isso o uvicorn tem de confiar no proxy (`FORWARDED_ALLOW_IPS`).

Os emails são enviados em segundo plano (4 *threads*, fila de 200): um servidor SMTP lento ou parado não atrasa os pedidos. Não há repetição automática: se o envio falhar ou a fila encher, o email perde-se e fica registado no log, e o utilizador pode pedir outro.

## Validação de dados

- **Nome:** é cortado nas pontas e tem de ter pelo menos uma letra. Recusa caracteres de controlo, invisíveis (por exemplo zero-width) e `<` ou `>`.
- **Password:** 8 a 200 caracteres (72 bytes no máximo), com maiúscula, dígito e símbolo. Um símbolo é qualquer carácter que não seja `A-Z`, `a-z` ou `0-9` (o espaço e as letras com acento contam). O erro 422 diz **todas** as regras de conteúdo que falharam: `{"type": "password_invalid", "ctx": {"rules": ["missing_uppercase", "missing_digit"]}}`, com os códigos `too_long`, `missing_uppercase`, `missing_digit` e `missing_symbol`. O comprimento (8 a 200) é verificado antes e tem erros próprios, sem `ctx` (`string_too_short`, `string_too_long`). O nome usa `name_invalid` com `blank`, `invalid_characters` e `no_letter`. No login a password só tem de ter 1 a 200 caracteres, e na mudança de password a `current_password` 8 a 200 (as regras de conteúdo só valem para passwords novas).
- **Email:** só caracteres ASCII (`email_not_ascii`), para não haver contas parecidas com letras de outros alfabetos. É guardado e comparado em minúsculas.

## Registar um email que ainda não foi verificado

Se alguém regista um email que nunca foi verificado, a conta passa para quem se regista agora (novo nome e nova password, e um email de verificação novo). Assim ninguém consegue manter o email de outra pessoa bloqueado. Os links antigos deixam de funcionar porque o token de verificação está ligado à password (campo `pwh`), e os links de recuperação pendentes e as sessões são fechados. Uma conta **já verificada** nunca é substituída (`409`).

## Contas não verificadas

Uma conta que nunca confirmou o email continua a ocupar esse email. O comando `make cleanup-unverified` (`python -m app.domains.users.cleanup`) apaga as contas não verificadas com mais de `UNVERIFIED_ACCOUNT_TTL_DAYS` dias (7 por omissão) e os tokens de recuperação de password que expiraram há mais de um dia (e os tokens de sessão revogados que já expiraram). Tem de correr uma vez por dia no servidor (ver `docs/deploy.md`, "Limpeza de contas não verificadas").

## Pagamentos

A bilheteira tem quatro modalidades (`acesso`, `refeicoes`, `completo`, `geral`), guardadas na tabela `tickets` e semeadas na migration a partir de `TICKET_PRICE_*_CENTS` (com IVA, em cêntimos). As três primeiras são de estudante.

- **Preço do servidor:** `POST /api/payment/initiate` ignora qualquer preço enviado pelo cliente e usa o da base de dados, multiplicado pela quantidade.
- **Stock atómico:** a verificação de disponibilidade e a reserva do lugar acontecem na mesma transação, com a linha do bilhete bloqueada (`SELECT ... FOR UPDATE`), por isso dois pedidos em simultâneo não podem vender mais do que o `inventory_limit`.
- **Estudante:** quem se regista com um email cujo domínio está em `STUDENT_EMAIL_DOMAINS` fica com `student_verification_status: "verified"` automaticamente; os outros ficam `pending` e não podem comprar bilhetes de estudante (recebem `403`). O estado é exposto em `GET /api/auth/me`.
- **MB WAY:** sem `MBWAY_KEY` o gateway é simulado (responde sempre `pending`, sem contactar nada); com `MBWAY_KEY` fala com a ifthenpay (`MBWAY_BASE_URL`). Os pagamentos pendentes duram `MBWAY_PAYMENT_TIMEOUT_SECONDS` (4 minutos por omissão) e depois expiram, libertando o lugar.
- O contrato detalhado está em [`docs/api-payments.md`](../docs/api-payments.md).

## Health checks

- `GET /api/health`: o processo responde, `{"status": "OK"}` (não toca na base de dados). É o que o `HEALTHCHECK` da imagem e o deploy usam.
- `GET /api/health/ready`: verifica a base de dados e devolve `503` (`{"detail": "Database unavailable"}`) se falhar.

## Comandos úteis

```bash
make dev          # arranca o servidor em modo desenvolvimento
make test         # corre os testes
make lint         # ruff check + format
make format       # ruff format
make db-upgrade   # aplica migrations
make db-revision m="descrição"   # cria nova migration
make cleanup-unverified   # apaga contas não verificadas antigas
make help         # lista todos os comandos
```

## Migrations

Em produção as migrations correm **antes** de o código novo ser posto no ar, por isso cada migration tem de funcionar com a versão anterior do código: acrescente colunas e tabelas, sem apagar nem renomear nada de uma vez. Um Pull Request com uma migration destrutiva falha no CI (`scripts/check_migrations.py`); se for mesmo preciso, marque-a com `# destructive: ok - motivo` e faça-a em dois deploys.
