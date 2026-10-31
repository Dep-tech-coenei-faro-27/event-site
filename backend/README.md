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

O CI também corre o fluxo completo (registo, verificação, login, compra nas cinco
modalidades com o gateway simulado, QR e email do bilhete) contra o servidor a sério,
numa base criada pelas migrations e sem mandar emails. Como funciona e como correr
localmente está em [`docs/testes-e2e.md`](../docs/testes-e2e.md).

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

| Endpoint | Limite | Variável |
| --- | --- | --- |
| `POST /auth/login` | 5 por minuto por email e IP | `RATE_LIMIT_LOGIN_PER_MINUTE` |
| | 20 por minuto por email (de qualquer IP) | `RATE_LIMIT_LOGIN_PER_EMAIL_PER_MINUTE` |
| | 60 por minuto por IP | `RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE` |
| `POST /auth/register` | 2 por minuto por IP | `RATE_LIMIT_REGISTER_PER_MINUTE` |
| `POST /auth/resend-verification-email` e `POST /auth/forgot-password` | 1 por minuto por email | `RATE_LIMIT_EMAIL_PER_MINUTE` |
| | 5 por hora por email | `RATE_LIMIT_EMAIL_PER_HOUR` |
| | 10 por minuto por IP | `RATE_LIMIT_EMAIL_PER_IP_PER_MINUTE` |
| `PUT /auth/password` | 2 por 15 minutos por utilizador | `RATE_LIMIT_PASSWORD_CHANGE_PER_15_MINUTES` |
| `POST /auth/verify-email` e `POST /auth/reset-password` | 20 por minuto por IP | `RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE` |
| `POST /payment/initiate` | 10 por minuto por utilizador | `RATE_LIMIT_PAYMENT_PER_MINUTE` |
| `GET /payment/transactions/{reference}` e o seu fluxo `/events` | 120 por minuto por utilizador (partilhado) | `RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE` |
| `GET /payment/tiers` | 600 por minuto por IP | `RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE` |
| `GET /payment/callback` | 60 por minuto por IP | `RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE` |

O limite de login conta o par email e IP, por isso alguém que falhe a password de outra pessoa não a bloqueia: só se bloqueia a si próprio.

Ao exceder o limite a API devolve `429` com o cabeçalho `Retry-After`. Os valores mudam com as variáveis da tabela (no `.env`) e `RATE_LIMIT_ENABLED=false` desliga os limites (útil em testes de carga). Atrás de um proxy o IP vem de `X-Forwarded-For`, por isso o uvicorn tem de confiar no proxy (`FORWARDED_ALLOW_IPS`).

Os emails são gravados numa fila na base de dados (tabela `email_outbox`) e enviados em segundo plano por um *worker*: um servidor SMTP lento ou parado não atrasa os pedidos, o email sobrevive a um reinício do backend e o que falhar é repetido com espera crescente (10 tentativas por omissão, cerca de 27 horas). Se esgotar as tentativas fica `failed` e o erro aparece no log. Como se vê o estado da fila e como são apagados os corpos está em [`docs/deploy.md`](../docs/deploy.md#email).

## Validação de dados

- **Nome:** é cortado nas pontas e tem de ter pelo menos uma letra. Recusa caracteres de controlo, invisíveis (por exemplo zero-width) e `<` ou `>`.
- **Password:** 8 a 200 caracteres (72 bytes no máximo), com maiúscula, dígito e símbolo. Um símbolo é qualquer carácter que não seja `A-Z`, `a-z` ou `0-9` (o espaço e as letras com acento contam). O erro 422 diz **todas** as regras de conteúdo que falharam: `{"type": "password_invalid", "ctx": {"rules": ["missing_uppercase", "missing_digit"]}}`, com os códigos `too_long`, `missing_uppercase`, `missing_digit` e `missing_symbol`. O comprimento (8 a 200) é verificado antes e tem erros próprios, sem `ctx` (`string_too_short`, `string_too_long`). O nome usa `name_invalid` com `blank`, `invalid_characters` e `no_letter`. No login a password só tem de ter 1 a 200 caracteres, e na mudança de password a `current_password` 8 a 200 (as regras de conteúdo só valem para passwords novas).
- **Email:** só caracteres ASCII (`email_not_ascii`), para não haver contas parecidas com letras de outros alfabetos. É guardado e comparado em minúsculas.

## Registar um email que ainda não foi verificado

Se alguém regista um email que nunca foi verificado, a conta passa para quem se regista agora (novo nome e nova password, e um email de verificação novo). Assim ninguém consegue manter o email de outra pessoa bloqueado. Os links antigos deixam de funcionar porque o token de verificação está ligado à password (campo `pwh`), e os links de recuperação pendentes e as sessões são fechados. Uma conta **já verificada** nunca é substituída (`409`).

## Contas não verificadas

Uma conta que nunca confirmou o email continua a ocupar esse email. O comando `make cleanup-unverified` (`python -m app.domains.users.cleanup`) apaga as contas não verificadas com mais de `UNVERIFIED_ACCOUNT_TTL_DAYS` dias (7 por omissão) e os tokens de recuperação de password que expiraram há mais de um dia (e os tokens de sessão revogados que já expiraram). Tem de correr uma vez por dia no servidor (ver `docs/deploy.md`, "Limpeza de contas não verificadas").

## Comprovativo de estudante

Quem não tem email de aluno envia o comprovativo de matrícula em `POST /api/users/me/student-proof` (contrato em [`docs/api-auth.md`](../docs/api-auth.md)). O ficheiro vai para `STUDENT_PROOF_DIR` (`/app/private/student-proofs`, o volume `./backend/private`), **fora de `media/`**, com nome aleatório e permissões só para o servidor; é apagado quando há decisão e fica o hash (SHA-256). Não há cópia de segurança desta pasta (são dados pessoais de vida curta).

**Pré-validação** (`app/domains/students/document.py`): lê as assinaturas do PDF com o pyHanko e só aprova sozinho se a assinatura estiver íntegra e cobrir o ficheiro todo, for um selo eletrónico qualificado (extensão `qcStatements` com `QcCompliance` e `QcType` selo) emitido por um serviço qualificado da lista de confiança da UE, o NIPC do selo (`organizationIdentifier`, `VATPT-NIPC`) já estiver registado numa instituição, o nome da conta estiver no texto, o ano letivo atual (a partir de agosto) estiver no texto e nenhuma outra conta tiver enviado o mesmo ficheiro. Não se consultam CRL/OCSP (sem rede no pedido). O que não passa fica `submitted`.

**Lista de confiança:** o ficheiro `app/domains/students/trust/eu_qualified_seals.pem` é uma fotografia dos serviços CA/QC concedidos nas listas nacionais da UE. Atualiza-se com `python -m app.domains.students.trust_list` (descarrega a LOTL e as listas nacionais por https) e a diferença revê-se no Pull Request: **as assinaturas das listas não são verificadas** pelo comando. `STUDENT_TRUST_ANCHORS_FILE` aponta para outro ficheiro, se for preciso.

**Instituições:** `app/domains/students/institutions.py` (nomes de `PortugueseInstitution`, siglas e variantes geradas por código; siglas de 5 letras ou menos só por igualdade). Ao início nenhum NIPC está registado: o primeiro comprovativo de cada instituição vai a revisão e, ao aprovar com `--institution`, o NIPC fica registado (`institution_nipcs`) e os seguintes passam sozinhos.

**Revisão** (no servidor, dentro do contentor do backend):

```bash
python -m app.domains.students.review list                       # os que esperam, com o motivo
python -m app.domains.students.review show ID                    # só dados da assinatura, nunca o nome do aluno
python -m app.domains.students.review export ID /tmp/prova.pdf   # copia o ficheiro para o abrir; fica registado
python -m app.domains.students.review approve ID [--institution CHAVE]   # NIPC novo exige --institution
python -m app.domains.students.review reject ID
```

`--reviewer NOME` (antes do comando) identifica quem decide; por omissão é o utilizador do sistema. O registo (`student_proof_events`) guarda quem viu, aprovou ou recusou e quando, sem dados pessoais. Apague o ficheiro exportado depois de o ver.

**Verificar um ficheiro sem rever o pedido:** `python -m app.domains.students.check_file FICHEIRO.pdf [--name "Nome"]` corre a mesma leitura na tua máquina e imprime só factos sem dados pessoais (assinatura, selo, NIPC, instituição, anos letivos, se menciona código de validação; com `--name`, só sim ou não). Serve para um colega testar o seu comprovativo e enviar apenas o resultado.

Os testes usam PDFs sintéticos assinados por uma autoridade de teste (`tests/student_pdfs.py`), sem dados pessoais. Os PDFs reais de instituições (com selo e com código de validação) não estão no repositório: `STUDENT_REAL_PROOFS_DIR` aponta para uma pasta fora dele (ver `tests/test_student_real_pdfs.py`).

## Pagamentos

A bilheteira tem cinco modalidades (`acesso`, `refeicoes`, `completo`, `geral`, `geral_refeicoes`), guardadas na tabela `ticket_tiers`. A migration cria as quatro primeiras com `price_cents` a `NULL` (bilheteira fechada); a quinta (`geral_refeicoes`) cria-se com o primeiro `set-price` (a migration só alarga a restrição, porque o código anterior não conhece o valor novo); o preço passa a estar definido com `make set-price tier=geral price=3500` (`python -m app.domains.payments.set_price`, com IVA, em cêntimos, sempre maior que zero). As três primeiras são de estudante; `geral` e `geral_refeicoes` são para não estudantes.

- **Bilheteira fechada:** enquanto `price_cents` for `NULL`, `POST /api/payment/initiate` responde `503` sem criar transação (nunca há uma transação de valor zero).
- **Preço do servidor:** `POST /api/payment/initiate` ignora qualquer preço enviado pelo cliente e usa o da base de dados, multiplicado pela quantidade.
- **Stock atómico:** a verificação de disponibilidade e a reserva do lugar acontecem na mesma transação, com a linha do bilhete bloqueada (`SELECT ... FOR UPDATE`), por isso dois pedidos em simultâneo não podem vender mais do que o `inventory_limit`.
- **Estudante:** quem se regista com um email cujo domínio está em `STUDENT_EMAIL_DOMAINS` fica com `student_verification_status: "verified"` automaticamente; os outros ficam `none` e não podem comprar bilhetes de estudante (recebem `403`), a não ser que enviem o comprovativo de matrícula (secção seguinte). O estado (`none`, `submitted`, `verified`, `rejected`) é exposto em `GET /api/auth/me` e `GET /api/users/me`.
- **Abertura da bilheteira:** `SALES_OPEN_AT` (data ISO 8601 com fuso, por exemplo `2026-11-02T09:00:00+00:00`). Antes dela as modalidades aparecem fechadas e `/payment/initiate` responde `503`; webhooks, estado e reembolsos não mudam. Sem a variável, não há data de abertura.
- **MB WAY:** o modo é `PAYMENTS_MODE` (`off` por omissão, `simulated` ou `live`). Em `off` a bilheteira responde `503`; em `simulated` o gateway responde sempre `pending`, sem contactar nada; em `live` fala com a ifthenpay (`MBWAY_KEY` e `MBWAY_BASE_URL` em `https`, obrigatórios). Os pagamentos pendentes duram `MBWAY_PAYMENT_TIMEOUT_SECONDS` (4 minutos por omissão) e depois expiram, libertando o lugar. Com `simulated`, `PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS` > 0 faz o gateway simulado confirmar o pagamento ao fim desses segundos, para testar a confirmação sem ifthenpay. Um pagamento com o telemóvel `910000000` nunca é confirmado pelo simulador: só expira. Só é permitido com `PAYMENTS_MODE=simulated`; com `live` ou `off` o backend recusa arrancar.
- **Callback do pagamento:** em `live` a ifthenpay confirma o pagamento chamando `GET /api/payment/callback` com a chave anti-phishing (`MBWAY_CALLBACK_KEY`, pelo menos 32 caracteres) e a referência. O endpoint é público, limita os pedidos por IP, compara a chave em tempo constante, valida o valor e é idempotente; só confirma transações `pending` (uma `failed` ou `expired` responde `200` mas fica intocada e com um aviso nos logs). A mesma função de confirmação é usada pelo *polling* (`GET /api/payment/transactions/{reference}`), por isso o bilhete com o QR assinado é emitido quer o pagamento chegue pelo callback quer pela consulta. Sem a chave configurada (ou em `live` sem `MBWAY_CALLBACK_KEY`) o callback é recusado com `403`. A chave é removida dos logs de acesso do uvicorn.
- **Email do bilhete:** quando o pagamento passa a confirmado, o email com o QR vai para a fila durável (`email_outbox`, `dedupe_key` `ticket:<id>`), nas cinco modalidades e nunca para um pagamento `refund_due`. É um `multipart/alternative`: texto simples (guardado em `text_body`, com os mesmos dados) e HTML com o QR inline (`cid:ticket-qr`). `text_body`, `html_body` e `inline_images` são apagados depois do envio e quando uma linha falhada é limpa. Se pôr o email na fila falhar, o bilhete já está emitido e o varrimento diário (`make cleanup-unverified`, `queue_missing_ticket_emails`) volta a pô-lo, sem duplicar. O desenho (o de `ui-ux/ticket-email/`, PR #287; estes dois ficheiros são cópias, 600 px, sem `rgba` nem imagem de fundo, QR de 240 px) está em `app/core/email/ticket_email.html` e `.txt`, com os marcadores `[FIRST_NAME]`, `[ATTENDEE_NAME]`, `[TICKET_TYPE]`, `[TICKET_REFERENCE]`, `[EVENT_DATES]`, `[EVENT_LOCATION]` e `[TICKET_URL]`; o renderizador escapa os valores e falha se um marcador ficar por substituir. O link do botão é `FRONTEND_URL` + `/perfil` (com ou sem barra final) e o HTML tem de ficar abaixo de 102 KB (o Gmail corta acima disso).
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
make set-price tier=geral price=3500   # abre a bilheteira dessa modalidade
make help         # lista todos os comandos
```

## Migrations

Em produção as migrations correm **antes** de o código novo ser posto no ar, por isso cada migration tem de funcionar com a versão anterior do código: acrescente colunas e tabelas, sem apagar nem renomear nada de uma vez. Um Pull Request com uma migration destrutiva falha no CI (`scripts/check_migrations.py`); se for mesmo preciso, marque-a com `# destructive: ok - motivo` e faça-a em dois deploys.
