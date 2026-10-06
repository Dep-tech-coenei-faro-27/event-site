# Deploy

Como o event-site chega ao servidor e como o operar. Está escrito para quem faz isto pela primeira vez, por isso lê-o até ao fim antes de mexeres no servidor.

## Visão geral

O site corre numa VPS com o Docker Compose, e o deploy é feito pelo GitHub Actions. O `docker-compose.yml` da raiz tem quatro serviços:

| Serviço | Imagem | O que faz |
| --- | --- | --- |
| `postgres` | `postgres:16-alpine` | A base de dados. Só fala com o backend, dentro do Docker. |
| `backend` | `backend/Dockerfile` | A API (FastAPI), como utilizador sem privilégios (uid 10001). Aplica as migrations ao arrancar. |
| `frontend` | `frontend/Dockerfile` | O nginx (sem root, porta 8080): serve o site e **encaminha `/api` e `/media` para o backend**. É a única porta de entrada para a internet, através do túnel. |

As portas publicadas no servidor (5432, 8000 e 8080) ficam todas ligadas a `127.0.0.1`: não são acessíveis de fora da máquina.
| `tunnel` | `cloudflare/cloudflared` | Liga o servidor à Cloudflare sem abrir portas. |

**O site e a API ficam no mesmo endereço** (por exemplo `https://eneifaro.pt` e `https://eneifaro.pt/api`). Por isso não há CORS entre eles, o cookie de sessão funciona sem configuração extra e o endereço da API não tem de ser configurado no build.

No painel da Cloudflare (Zero Trust, Tunnels, rotas de aplicação publicadas), o endereço público do túnel tem de apontar para **`http://frontend:8080`**. Se apontar para o backend, o site não aparece.

## Como funciona o deploy

O `.github/workflows/cd.yml` corre depois de o "CI - Backend" passar num push para `dev` ou `main` (ou à mão, em Actions, com "Run workflow"). Há um só deploy de cada vez.

**`dev` e `main` fazem deploy para o mesmo servidor e para a mesma pasta.** O último a correr ganha. Enquanto houver um só ambiente, não faças merge para `main` sem querer que isso fique no ar.

Os passos, por ordem:

1. Copia o código para `/home/debian/enei/event-site` e escreve o `backend/.env` e o `tunnel.env` (permissões 600) a partir dos Secrets do repositório.
2. **Constrói as imagens novas e confirma que o backend aceita o `.env`**, tudo antes de parar o que está a correr. Se faltar um segredo ou for inseguro, o deploy pára aí e o site atual continua de pé.
3. **Aplica as migrations antes de trocar o código** (num contentor descartável com a imagem nova). Se falharem, o site que está a correr não foi parado e a base de dados ficou como estava.
4. Faz `down` e `up -d --build`. Há cerca de 15 segundos sem site em cada deploy.
5. Só dá o deploy por bom se o `/api/health` responder (testado por dentro do contentor). Se não responder, o job falha e mostra o log do backend.

Como as migrations correm antes de trocar o código, **cada migration tem de funcionar com a versão anterior do código** (acrescentar colunas e tabelas, sem apagar nem renomear). Nos Pull Requests, o passo "New migrations are safe for the previous code" (`scripts/check_migrations.py`) recusa `drop_column`, `drop_table`, renomeações e semelhantes. Se tiver mesmo de ser, a linha (ou a linha de cima) leva um comentário `# destructive: ok - motivo`, e deve ser feito em dois deploys. O CI também aplica todas as migrations a uma base vazia, confirma que não há diferenças em relação aos modelos e testa o `downgrade` (passo "Check migrations").

## Secrets do repositório

Estão em Settings, Secrets and variables, Actions, e **nunca vão para o Git**. Um segredo em falta fica vazio no `.env`, e é o passo 2 acima que o apanha.

- **Acesso à VPS:** `VPS_HOST`, `VPS_USERNAME`, `VPS_PASSWORD`, `VPS_SSH_PORT`.
- **Túnel:** `TUNNEL_TOKEN`.
- **Base de dados:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- **Sessões e tokens:** `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES`, `JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`.
- **Email:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_SENDER`.
- **Resto:** `PROJECT_NAME`, `DEBUG`, `FRONTEND_URL`, `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS`.

Regras para criar os valores:

- `JWT_SECRET_KEY` novo, com 32 ou mais caracteres (nunca o do `.env.example`): `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `POSTGRES_PASSWORD` própria (em produção não pode ser `postgres`).
- Nunca faças commit de um `.env`. Se um segredo aparecer num commit ou num log, trata-o como roubado e troca-o.
- O GitHub esconde nos logs qualquer texto igual ao valor de um segredo (por exemplo, todos os `1` aparecem como `***` se um segredo for `1`). É normal.

## Variáveis do backend

Com `ENVIRONMENT=prod` (o valor por omissão) o backend **não arranca** se alguma regra de segurança falhar, e a mensagem de erro diz qual.

| Variável | Produção | Notas |
| --- | --- | --- |
| `ENVIRONMENT` | `prod` | Em `dev` escreve-se `ENVIRONMENT=dev` (o `.env.example` já o faz). Em `prod` o `/docs` e o `/openapi.json` não existem. |
| `DEBUG` | `false` | Com `true` as respostas mostram tracebacks, e o arranque em produção recusa-o. |
| `JWT_SECRET_KEY` | obrigatório | Pelo menos 32 caracteres e diferente dos valores de exemplo. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` | obrigatórios | `POSTGRES_HOST` é o nome do serviço no compose (`postgres`). |
| `FRONTEND_URL` | `https://...` | Usado nos links dos emails. Tem de ser `https`. |
| `CORS_ALLOW_ORIGINS` | `https://...` | Lista (JSON ou separada por vírgulas) com as origens do frontend. Nunca aceita `*`, e em produção todas têm de ser `https`. Com o site e a API no mesmo endereço, quase não se usa. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_SENDER` | obrigatórios | `SMTP_HOST` e `EMAIL_SENDER` são obrigatórios em produção. |
| `SMTP_SECURITY` | `auto` | `auto` usa TLS direto na porta 465 e STARTTLS nas outras. Também aceita `starttls` e `ssl`. `none` só serve para o Mailpit local e é recusado em produção. |
| `SMTP_TIMEOUT_SECONDS` | `5` | Tempo máximo de espera pelo servidor SMTP. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_ACCESS_TOKEN_LONG_EXPIRE_MINUTES` | `60`, `10080` | Duração da sessão: 60 minutos, ou 7 dias com "lembrar-me". |
| `JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `30`, `15` | Validade dos links dos emails. |
| `FORWARDED_ALLOW_IPS` | `172.16.0.0/12` (valor da imagem) | Ver "IP dos visitantes". |
| `RATE_LIMIT_*` | opcional | Limites de pedidos (ver `docs/api-auth.md`). Mantém `RATE_LIMIT_ENABLED=true`. |
| `MAX_REQUEST_BYTES` | `1048576` | Tamanho máximo do corpo de um pedido (1 MB). Acima disso a API responde `413`. O nginx tem o mesmo limite. |
| `UNVERIFIED_ACCOUNT_TTL_DAYS` | `7` | Dias até as contas não verificadas serem apagadas. |

A lista completa e os valores por omissão estão em `backend/app/core/config.py`.

## IP dos visitantes

Os limites de pedidos contam por IP, e o IP real chega no cabeçalho `X-Forwarded-For` (Cloudflare, depois nginx, depois backend). A imagem do backend já confia nas redes privadas do Docker (`FORWARDED_ALLOW_IPS=172.16.0.0/12`), por isso cada visitante conta em separado. Se o valor deixar de estar certo, o backend avisa no arranque (`FORWARDED_ALLOW_IPS`), porque todos os visitantes passariam a partilhar o mesmo limite.

Só mudes isto se pores um proxy fora do Docker. E só uses `FORWARDED_ALLOW_IPS=*` se o backend **não** for acessível sem passar pelo proxy, senão qualquer pessoa inventa o cabeçalho e foge aos limites.

## Migrations

O `docker-entrypoint.sh` corre `alembic upgrade head` sempre que o contentor arranca, e o CD também as corre antes de trocar o código (sem nada para migrar, não faz nada). Se uma migration falhar, o contentor pára em vez de servir sobre uma base mal migrada.

- Se alguma vez correres mais do que um contentor do backend, define `RUN_MIGRATIONS=false` em todos menos um.
- Para ver o estado: `$COMPOSE exec -T backend /app/.venv/bin/alembic current` (o `$COMPOSE` está definido em "Comandos na VPS").
- **Faz uma cópia de segurança antes de um deploy com migrations novas** (ver "Cópias de segurança").

## Comandos na VPS

Todos na pasta do projeto:

```bash
cd ~/enei/event-site
COMPOSE="docker compose --env-file backend/.env --env-file tunnel.env"

$COMPOSE ps                       # estado dos contentores
$COMPOSE logs --tail 50 backend   # logs do backend
$COMPOSE restart backend          # reiniciar (as migrations voltam a correr, sem efeito)
```

## Frontend

A imagem tem duas fases: compila com `npm run build` e serve o resultado com nginx (sem root, porta 8080).

- A API fica no mesmo endereço do site (`/api`), por isso **não é preciso** configurar o endereço da API. Só se a API estiver noutro endereço é que se define `VITE_API_URL` no build.
- O nginx envia o `Content-Security-Policy`, o HSTS e os restantes cabeçalhos de segurança. Se o frontend passar a carregar mais alguma origem (mapa, vídeo, analytics), é preciso acrescentá-la ao CSP em `frontend/nginx.conf.template`.
- As rotas do React Router funcionam (`/login` devolve o `index.html`), mas ficheiros que não existem (`/assets/x.js`) devolvem `404`.
- Os links dos emails levam o token no URL (`/conta/verificar?token=...`), por isso o log de acessos do nginx guarda esses tokens. Mantém os logs privados e com retenção curta.

## Ficheiros enviados (media)

O backend serve as imagens de `backend/media` (montada em `/app/media`) em `/media`. Só são servidas imagens (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.avif`; qualquer outra extensão e ficheiros escondidos dão `404`), com `Content-Security-Policy: sandbox`, `nosniff` e cache de um dia.

O contentor corre com o utilizador `app` (uid 10001). Hoje nada escreve nesta pasta, por isso basta ler. **Quando houver uploads**, ou dás a pasta ao uid 10001 (`sudo chown -R 10001 backend/media`), ou passas a um volume com nome (`media:/app/media`), que herda o dono certo. A pasta tem de sobreviver aos deploys, e entra nas cópias de segurança.

## Limpeza de contas não verificadas

As contas que nunca confirmaram o email (e os tokens de recuperação e de sessão expirados) são apagadas por um comando que tem de correr todos os dias. Sem ele as contas acumulam-se e quem se registou com um email que não é seu bloqueia esse email.

No servidor, com o cron do sistema (`sudo apt-get install -y cron && sudo systemctl enable --now cron`), uma linha no `crontab -e` do utilizador `debian`:

```
0 4 * * * cd /home/debian/enei/event-site && docker compose --env-file backend/.env --env-file tunnel.env exec -T backend /app/.venv/bin/python -m app.domains.users.cleanup >> /home/debian/enei/cleanup.log 2>&1
```

Para confirmar que funciona: `crontab -l`, `systemctl is-active cron`, e corre o comando uma vez à mão. Deve imprimir `Deleted N unverified accounts older than 7 days and ...`. No dia seguinte, o `cleanup.log` tem uma linha dessas com a data do dia. As horas do cron são as do fuso do servidor (`date`).

## Cópias de segurança

`scripts/backup.sh` guarda a base de dados (`db-<data>.dump`) e a pasta `backend/media` (`media-<data>.tar.gz`) em `backups/`, só legíveis por quem as cria:

```bash
sh scripts/backup.sh               # ou: sh scripts/backup.sh /outra/pasta
```

- **Um backup que nunca foi restaurado não conta.** `scripts/restore.sh` restaura para uma base **nova** (recusa uma que já exista), por isso podes testar sem tocar na base verdadeira:
  ```bash
  sh scripts/restore.sh backups/db-AAAAMMDD-HHMMSS.dump teste_restauro
  $COMPOSE exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d teste_restauro -c "SELECT count(*) FROM users"'
  $COMPOSE exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" teste_restauro'
  ```
- Para repor a base verdadeira: pára o backend (`$COMPOSE stop backend`), apaga a base (`dropdb`) e restaura com o mesmo nome da base original. Em caso de dúvida, restaura para um nome novo e decide depois.
- As cópias têm dados pessoais: não as ponhas no Git nem as partilhes. Copia-as para **fora do servidor**, porque uma cópia no mesmo disco não protege contra a perda do disco.
- Agendar as cópias (por exemplo com o cron, como a limpeza) e guardá-las fora do servidor ainda é trabalho por fazer.

## Email

- O envio é assíncrono: o pedido responde logo e o email segue em segundo plano (4 *threads* e uma fila de 200 emails). **Não há repetição automática**: se o servidor SMTP estiver em baixo, ou a fila encher, ou o backend reiniciar com emails na fila, esses emails perdem-se. O erro fica nos logs (`Failed to send email`, ou `Email queue is full`) e o utilizador pode pedir um novo email.
- O certificado do servidor SMTP é verificado. Um servidor com certificado autoassinado vai falhar.
- Está configurado o **Resend** (`SMTP_HOST=smtp.resend.com`, `SMTP_PORT=465`, `SMTP_USER=resend`, `SMTP_PASSWORD` a chave de API). O remetente (`EMAIL_SENDER`) tem de ser de um domínio verificado no Resend (`noreply@mail.eneiconf.pt`), senão o Resend recusa o envio. O plano gratuito tem limites de envio diários: confirma-os antes do evento.
- Em desenvolvimento, sem `SMTP_HOST`, os emails aparecem no log do backend, com os links. Com o `docker-compose.dev.yml`, ficam no Mailpit em `http://localhost:8025`.

## Verificar um deploy

1. No GitHub, em Actions, o "CD" fica verde e o log tem `backend OK`.
2. Na VPS:
   ```bash
   $COMPOSE ps                                                   # tudo "running", backend "healthy"
   $COMPOSE exec -T backend id                                   # uid=10001(app)
   $COMPOSE logs backend 2>&1 | grep -E "Traceback|ERROR"        # sem resultados
   ```
3. De fora: `https://<site>/api/health` responde `200` (`{"status":"OK"}`), `https://<site>/api/health/ready` também (confirma a base de dados), e `curl -sI https://<site>/` mostra `Strict-Transport-Security` e `Content-Security-Policy`.
4. Regista uma conta de teste: o email chega e o link verifica-a (ver `docs/api-auth.md`).

## Antes do evento

- [ ] `JWT_SECRET_KEY`, password da base de dados e SMTP novos (não os do repositório), `ENVIRONMENT=prod`, `DEBUG=false`.
- [ ] `FRONTEND_URL` e `CORS_ALLOW_ORIGINS` com o endereço final em `https`, e o túnel a apontar para `http://frontend:8080`.
- [ ] Sem o aviso `FORWARDED_ALLOW_IPS` no log do arranque.
- [ ] Base de dados sem porta pública (só `127.0.0.1`).
- [ ] Limpeza diária no cron e confirmada.
- [ ] Cópias de segurança agendadas, guardadas fora do servidor, e um restauro testado.
- [ ] Limites do plano de email (Resend) confirmados para o número de inscrições esperado.
- [ ] Muita gente na mesma rede (campus): cada IP partilhado conta como uma só pessoa. Se for preciso, sobe `RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE` e `RATE_LIMIT_REGISTER_PER_MINUTE`.
- [ ] Uma regra de limite de pedidos na Cloudflare para `/api/auth/*`, como segunda barreira à frente do servidor.

## Reverter um deploy

1. **O código:** reverte o merge em `dev` (`git revert` num Pull Request). O CI e o CD voltam a pôr a versão anterior no ar. Só uses "Run workflow" a partir de um ramo que tenha a versão atual do `cd.yml`: um ramo antigo corre o `cd.yml` dele, sem as verificações antes do `down`.
2. **A base de dados:** como as migrations têm de ser compatíveis com o código anterior, normalmente não é preciso desfazê-las. Se for mesmo preciso, pára o backend e desce uma migration antes de pores o código antigo:
   ```bash
   $COMPOSE stop backend
   $COMPOSE run --rm --no-deps --entrypoint /app/.venv/bin/alembic backend downgrade -1
   ```
3. Em caso de dúvida sobre os dados, restaura a cópia de segurança feita antes do deploy (ver "Cópias de segurança").

Nunca cancele um deploy a meio depois de aparecer `Removed`: o site fica em baixo até outro deploy acabar.
