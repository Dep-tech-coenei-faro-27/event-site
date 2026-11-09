# Teste de carga

Quantas inscrições, inícios de sessão e compras por minuto o backend aguenta, medido contra o servidor real (uvicorn,
um só processo, como no `Dockerfile`) sobre uma base PostgreSQL nova criada pelas migrations. Os números medidos e as
conclusões estão em [`RESULTADOS.md`](RESULTADOS.md).

| Ficheiro       | O que faz                                                                                                   |
|----------------|-------------------------------------------------------------------------------------------------------------|
| `run.sh`       | Cria a base `loadtest_*`, corre as migrations, cria as contas, arranca o servidor, corre um cenário, apaga a base. |
| `loadtest.py`  | O cliente de carga (só a biblioteca padrão para o HTTP) e as verificações no fim.                            |
| `seed.py`      | Contas verificadas e a modalidade `geral` à venda. Recusa uma base cujo nome não comece por `loadtest`.        |
| `report.py`    | Gráficos SVG e a tabela em Markdown a partir dos resultados.                                                 |

## Segurança

- **O alvo é sempre explícito.** Por omissão é `http://127.0.0.1:8000`; outro endereço que não seja esta máquina
  precisa também de `--remote`. Nunca contra a produção: no servidor o staging e a produção partilham a base de dados.
- **Nenhum email sai**: `run.sh` arranca o servidor com `SMTP_HOST` e `SMTP2_HOST` vazios, e os emails só vão para o log.
  As contas são de `loadtest.example.com`, um domínio reservado.
- **Nenhum pagamento é real**: `PAYMENTS_MODE=simulated`. O fornecedor simulado demora `LATENCY` segundos a responder
  (`PAYMENTS_SIMULATED_LATENCY_SECONDS`, que só é aceite em `simulated`) e dá o pagamento como pago ao fim de
  `CONFIRM_AFTER` segundos.

## Correr

Precisa do PostgreSQL local (o do `docker-compose.dev.yml`) e do `backend/.venv`. Os dados de ligação vêm do
`backend/.env`; os limites, o pool e os tempos são os por omissão do código (os de produção), mesmo que o `.env` local
tenha outros.

```bash
scripts/loadtest/run.sh login
```

```bash
LATENCY=9 scripts/loadtest/run.sh payments --label "latência 9 s"
```

```bash
scripts/loadtest/run.sh campus --users 300 --over 60
```

Cenários (`--users` pessoas, por omissão 300, a chegar ao longo de `--over` segundos, por omissão 10):

| Cenário    | Cada pessoa…                                                                                       |
|------------|----------------------------------------------------------------------------------------------------|
| `login`    | inicia sessão (o bcrypt gasta cerca de 0,2 s de CPU).                                              |
| `payments` | já com sessão, inicia uma compra e segue o estado em tempo real (SSE) até o pagamento acabar.        |
| `sse`      | com um pagamento à espera, abre a ligação SSE ao mesmo tempo que as outras e mantém-na `--hold` s.   |
| `register` | cria uma conta (cada uma escreve um email na `email_outbox`, que o worker envia em série).          |
| `mix`      | `payments`, `login` e `register` ao mesmo tempo, e leituras de `/api/payment/tiers`.                 |
| `campus`   | lê as modalidades e inicia sessão, todas a partir do mesmo IP (uma rede atrás de um NAT).           |

Cada pessoa manda o seu `X-Forwarded-For` (o uvicorn confia nele vindo de 127.0.0.1), por isso os limites por IP veem
pessoas diferentes, menos no `campus`. Para medir outro limite, exporta-o antes: por exemplo
`RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE=300 scripts/loadtest/run.sh campus`.

Os resultados (JSON com cada pedido) e o log do servidor ficam em `scripts/loadtest/results/`, fora do Git. Para os
gráficos:

```bash
backend/.venv/bin/python scripts/loadtest/report.py scripts/loadtest/results/*.json --charts scripts/loadtest/charts
```

## Critérios

O `loadtest.py` sai com 1 se algum falhar:

- menos de 1 % de respostas 5xx (ou sem resposta);
- `/api/health/ready`, perguntado de meio em meio segundo, responde sempre em menos de 1 s;
- o pool de ligações nunca esgota (nenhum `QueuePool limit` no log do servidor) e não há erros sem tratamento;
- no fim nenhuma ligação fica `idle in transaction`;
- todos os pagamentos acabam resolvidos (nenhum `pending`) e a fila de emails esvazia.

## No staging

A mesma coisa contra o staging precisa de uma base própria: no servidor o staging e a produção partilham a base, e um
teste de carga criaria contas, pagamentos e emails verdadeiros. Só com uma VPS ou base de staging separada, com
`SMTP_HOST` vazio e `PAYMENTS_MODE=simulated`, e com `--base https://… --remote`.
