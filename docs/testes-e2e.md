# Teste do fluxo completo (ponta a ponta)

O teste `backend/tests/e2e/full_flow.py` percorre o caminho de quem compra um bilhete, à API, contra o **servidor a sério** (uvicorn) e uma base PostgreSQL **criada pelas migrations**. Corre no CI em cada Pull Request e em cada push para `dev` e `main` (passo «End-to-end flow» de `.github/workflows/ci-backend.yml`), depois do teste de fumo e sobre a mesma base, que se deita fora com o job.

## O que verifica

Para cada uma das cinco modalidades (três de estudante, com um email do domínio de aluno, e duas gerais), uma pessoa nova:

1. regista-se e não consegue entrar antes de confirmar o email (`403`);
2. tira o link de verificação do email que ficou na fila (`email_outbox`); um token alterado dá `400`;
3. verifica a conta e entra (o cookie de sessão);
4. inicia o pagamento MB WAY, que fica `pending`, e um segundo pagamento é recusado (`409`);
5. o gateway simulado confirma o pagamento; `GET /users/me` tem o `qr_code`, que verifica com `verify_qr_payload` para o bilhete emitido;
6. o email do bilhete está na fila, com a imagem do QR; uma segunda compra é recusada (`409`);
7. sai, e a sessão antiga passa a dar `401`.

Depois as falhas:

- **entradas inválidas:** modalidade de estudante sem estatuto de estudante (`403`), telemóvel inválido e modalidade que não existe (`422`), pagamento que não existe (`404`);
- **um pagamento que expira liberta o lugar:** com um único lugar livre, um pagamento que nunca é aprovado ocupa-o (a modalidade fica sem lugares e outra pessoa recebe `409`); quando expira, a outra pessoa compra o lugar;
- **modalidade esgotada:** depois disso a modalidade fica esgotada e uma terceira pessoa recebe `409`;
- **duas compras ao mesmo tempo** da mesma pessoa: só uma avança (`201` e `409`).

Demora uns 10 segundos e falha se passar de 2 minutos.

## Sem relógio real e sem emails

- **O tempo passa na base de dados.** O gateway simulado não guarda estado: lê o instante em que o pagamento foi criado da sua própria referência (`SIM-<instante>-<referência>`). Para «esperar» `N` segundos, o teste recua esse instante e o `expires_at` do pagamento `N` segundos. Não há `sleep` nem espera pelo relógio.
- **O servidor confirma os pagamentos** (`PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS=60`), menos os feitos com o telemóvel **`910000000`**, que nunca são aprovados e só expiram (ao fim de `MBWAY_PAYMENT_TIMEOUT_SECONDS`). Também serve ao frontend para ver o ecrã de pagamento expirado.
- **Nenhum email sai.** Sem `SMTP_HOST`, o envio só escreve no log, e com `EMAIL_OUTBOX_WORKER=0` os emails ficam na fila, de onde o teste os lê.

O teste recusa correr se não tiver a certeza de que está numa base descartável: `E2E_DISPOSABLE_DB` tem de ser igual a `POSTGRES_DB`, o `ENVIRONMENT` tem de ser `dev`, `PAYMENTS_MODE` tem de ser `simulated` (com o modo de confirmação) e não pode haver servidor de email. Os emails das contas são do domínio `example.com` ou do domínio de aluno configurado, com um sufixo aleatório por corrida, e não aparecem no output.

## Correr localmente

Numa base temporária (nunca na de desenvolvimento), a partir de `backend/`:

```bash
docker exec event-site-postgres-1 psql -U postgres -c "CREATE DATABASE e2e_tmp"
```

```bash
export ENVIRONMENT=dev POSTGRES_DB=e2e_tmp E2E_DISPOSABLE_DB=e2e_tmp \
  PAYMENTS_MODE=simulated PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS=60 \
  PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS=0 STUDENT_EMAIL_DOMAINS=ualg.pt \
  RATE_LIMIT_REGISTER_PER_MINUTE=100 RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE=200 \
  RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE=100 SMTP_HOST= SMTP2_HOST= EMAIL_OUTBOX_WORKER=0
```

```bash
uv run alembic upgrade head && E2E_PORT=8765 sh ../scripts/e2e-full-flow.sh
```

```bash
docker exec event-site-postgres-1 psql -U postgres -c "DROP DATABASE e2e_tmp"
```

`scripts/e2e-full-flow.sh` arranca o uvicorn (recusa uma porta já ocupada), espera que responda, corre o teste e, se falhar, mostra os registos do servidor. Os limites de pedidos sobem porque todas as contas do teste vêm do mesmo IP. O teste pode correr mais de uma vez na mesma base.
