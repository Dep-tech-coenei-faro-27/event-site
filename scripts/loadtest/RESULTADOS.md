# Teste de carga: resultados

Medido a 27/10/2026 **num portátil** (AMD Ryzen 7 5700U, 8 núcleos e 16 threads, 15 GB de RAM) e **não na VPS**. O
cliente de carga e o PostgreSQL corriam na mesma máquina que o servidor. Os números absolutos na VPS vão ser outros
(menos núcleos, rede a sério); o que vale aqui são as proporções, os pontos de saturação e o comportamento sob falha.
Como repetir: [`README.md`](README.md).

Configuração: o servidor real com o comando do `Dockerfile` (um só processo do uvicorn, as 40 threads do anyio), sobre
uma base PostgreSQL 16 nova criada pelas migrations, e com os limites, o pool (20 + 20) e os tempos por omissão do
código. Sem SMTP (os emails vão para o log) e com `PAYMENTS_MODE=simulated`. O fornecedor simulado demora `LATENCY`
segundos por chamada e dá o pagamento como pago ao fim de 5 s. Cada pessoa tem o seu IP, exceto no cenário do campus.

## Pico esperado

Há 300 compras iniciadas em 10 s, a referência da issue #118. Ao mesmo tempo há 300 inícios de sessão, 30 inscrições
novas (as inscrições espalham-se pelas semanas antes) e leituras de `/api/payment/tiers` de 5 em 5 por segundo. Todas
as compras seguem o estado por SSE até ao fim.

| Pedido | N | Estados | p50 | p95 | máx. |
|---|---|---|---|---|---|
| `POST /payment/initiate` (fornecedor a 1 s) | 300 | 201×300 | 1,02 s | 1,09 s | 1,19 s |
| `POST /auth/login` | 300 | 200×300 | 0,24 s | 0,28 s | 0,34 s |
| `POST /auth/register` | 30 | 201×30 | 0,25 s | 0,30 s | 0,34 s |
| `GET /payment/tiers` | 429 | 200×429 | 0,01 s | 0,02 s | 0,07 s |
| `GET /api/health/ready` | 207 | 200×207 | 0,005 s | 0,015 s | 0,046 s |

**Todos os critérios cumpridos.** Há 0 % de 5xx e o `/ready` fica sempre abaixo de 50 ms. O máximo é de 20 ligações à
base (o pool tem 40), sem nenhum `QueuePool limit` nem ligações presas. Os 300 pagamentos acabaram `confirmed`, com 300
bilhetes. Os 330 emails (300 bilhetes e 30 verificações) saíram todos da fila.
Gráfico: [`charts/09-pico-esperado.svg`](charts/09-pico-esperado.svg).

## Todos os cenários (com as correções deste PR)

| Cenário | Resultado | `/ready` máx. | Ligações máx. | Gráfico |
|---|---|---|---|---|
| 300 compras em 10 s, fornecedor a **1 s** | 300×201, p95 1,13 s; 300 confirmadas | 0,06 s | 13 | [02](charts/02-compras-1s.svg) |
| 300 compras em 10 s, fornecedor a **9 s** | 300×201, p50 32 s, máx. 63 s; 300 confirmadas | 0,09 s | 13 | [03](charts/03-compras-9s.svg) |
| 300 compras em 10 s, fornecedor a **30 s** (> timeout de 10 s) | 300×502 ao fim do timeout; 300 `failed`, nenhuma pendente | 0,02 s | 8 | [04](charts/04-compras-30s.svg) |
| 300 inícios de sessão em 10 s | 300×200, p95 0,34 s | 0,02 s | 13 | [05](charts/05-login.svg) |
| 600 inícios de sessão em 3 s (saturação) | 600×200, p95 7,9 s | **5,2 s** | 40 | [06](charts/06-login-saturacao.svg) |
| 300 ligações SSE abertas ao mesmo tempo | 299 abertas (primeiro byte p95 15 ms), todas até `confirmed` | 0,05 s | 12 | [07](charts/07-sse.svg) |
| 300 inscrições em 10 s | 300×201, p95 0,36 s; 300 emails enviados | 0,02 s | 14 | [08](charts/08-registo.svg) |
| 300 compras, 300 logins e 300 inscrições em 10 s (saturação) | 0 erros; login p95 3,0 s | **2,7 s** | 40 | [10](charts/10-mistura-saturacao.svg) |
| Campus: 300 pessoas num IP em 60 s, limites novos | tiers 300×200, login 300×200 | 0,04 s | 3 | [12](charts/12-campus-depois.svg) |

A 30 s, os 502 são o fornecedor em baixo e não o servidor: cada compra falha depois de `MBWAY_TIMEOUT_SECONDS` e o resto
do site continua normal. Por isso esse cenário só "falha" o critério dos 5xx por definição.

## Onde satura

- **CPU do bcrypt.** Cada início de sessão ou inscrição gasta 0,20 s de CPU (medido: `verify_password`, custo 12). O
  portátil faz 60 a 80 por segundo com as 40 threads. Acima disso os pedidos fazem fila nas threads partilhadas e o
  `/ready` também espera por uma: 600 logins em 3 s levaram o `/ready` a 5,2 s, sem nenhum erro. O pico esperado (30
  por segundo) fica a metade disso.
- **Fornecedor lento.** Cada compra ocupa uma das 40 threads de pagamento durante a chamada, por isso o débito é
  40 ÷ latência: 40/s a 1 s, 4,4/s a 9 s e 4/s a 30 s (quando cada uma desiste aos 10 s). A 9 s, a última das 300
  compras esperou 63 s, abaixo dos 100 s da Cloudflare.
- **Confirmação sem webhook.** Sem webhook (o simulador só confirma quando lhe perguntam), a confirmação depende da
  reconciliação. Esta pergunta 4 pagamentos de cada vez. A 1 s, as 300 confirmações levaram até 81 s; a 9 s, até 10
  minutos (algumas ligações SSE chegaram ao limite de 600 s e o browser volta a ligar). Em produção quem confirma é o
  webhook do Stripe (ou o callback da ifthenpay), na hora; a reconciliação é a rede de segurança.
- **Fila de emails.** Cada inscrição e cada bilhete escrevem uma linha em `email_outbox`; o worker envia uma de cada
  vez. Sem SMTP, 300 emails saíram em 10 s, por isso o próprio worker não é o gargalo. Com SMTP, o tempo de esvaziar a
  fila é cerca de 300 × o tempo de envio de um email (não medido aqui, porque o teste não pode mandar emails). Por
  exemplo, a 0,5 s por email seriam 2,5 minutos de atraso no fim do pico. Os pedidos não esperam pelo envio.

## O que estava abaixo do esperado e foi corrigido

Antes das correções, 300 compras em 10 s com o fornecedor a 9 s **paravam a API toda**. Houve 192 respostas 500, 69
pedidos sem resposta em 60 s, o `/ready` a 30 s, 245 `QueuePool limit` no log e ligações `idle in transaction` até 51 s
([`charts/01-compras-9s-antes.svg`](charts/01-compras-9s-antes.svg)). Era o bloqueio que o comentário do `DB_POOL_SIZE`
já descrevia, agora com a causa à vista:

1. **A autenticação segurava uma ligação.** `get_current_session` corre numa thread e deixava a transação de leitura
   aberta; o endpoint espera depois por outra thread. Com as 40 threads ocupadas, cada pedido em espera segurava uma
   ligação, e as threads que precisavam de uma ligação para acabar ficavam sem nenhuma. Agora termina a leitura
   (`commit`) antes de devolver.
2. **`initiate_payment` segurava uma ligação durante a chamada ao fornecedor.** O `db.refresh` depois do `commit`
   abria uma nova transação, e a ligação ficava presa os 9 s da chamada, ao contrário do que o comentário dizia. Agora
   termina-a antes de chamar o fornecedor.
3. **As compras ocupavam as threads de toda a gente.** `POST /payment/initiate` corre agora em threads próprias
   (`PAYMENT_INITIATE_THREADS`, 40): um fornecedor lento só atrasa as compras. Estas threads só usam uma ligação em
   leituras e escritas curtas. A 9 s usaram no máximo 13 ligações, por isso o pool continua dimensionado para as 40
   threads partilhadas.

Só com a correção 1, a 9 s continuava a esgotar o pool (122 respostas 500); foi a corrida que mostrou a 2. Com as três,
os mesmos 9 s ficam sem nenhum erro e com o `/ready` abaixo de 0,1 s.

## Limites por IP

Atrás de um NAT (a rede de um campus, o recinto do evento) toda a gente partilha o mesmo IP. O cenário do campus põe
300 pessoas no mesmo IP a abrir a página da loja e a iniciar sessão, ao longo de um minuto:

| Limite | Antes | Medido com o antigo | Novo | Medido com o novo |
|---|---|---|---|---|
| `RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE` | 60 | 60×200, **240×429** | 600 | 300×200 |
| `RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE` | 60 | 60×200, **240×429** | 300 | 300×200 |

Com os limites antigos, 4 em cada 5 pessoas do campus viam a página da loja falhar e não conseguiam entrar durante um
minuto. Para o servidor, essa carga é pequena: login p95 0,31 s, tiers 11 ms e 3 ligações à base.

- **`/tiers`, 600 por minuto por IP.** Cada leitura custa cerca de 10 ms, por isso 10 por segundo de um só IP são
  ~0,1 s de CPU por segundo. O limite só tem de travar um abuso óbvio.
- **Login, 300 por minuto por IP.** 5 por segundo × 0,2 s de bcrypt dá cerca de 1 núcleo, ~7 % do que o portátil
  aguenta (60 a 80 logins/s). Adivinhar a password de uma conta continua travado pelos limites por email (5 por minuto
  por email e IP, 20 por email de qualquer IP), que não mudaram. Atrás do servidor fica a regra da Cloudflare para
  `/api/auth/*` (lista «Antes do evento» em `docs/deploy.md`).
- **Inscrição, 2 por minuto por IP: sem alteração.** As inscrições espalham-se pelas semanas antes do evento e cada
  uma manda um email, por isso não há medição que justifique subir. Para uma sessão de inscrições em sala, sobe-se
  `RATE_LIMIT_REGISTER_PER_MINUTE` nesse dia.
- **Callback da ifthenpay, 60 por minuto por IP: sem alteração.** A produção usa o Stripe, cujos webhooks válidos nunca
  contam. Com a ifthenpay, 300 confirmações no mesmo minuto vindas dos poucos IPs dela passariam o limite e seriam
  repetidas mais tarde; nesse caso convém subir `RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE`.

## Um só processo

Mantém-se um só processo do uvicorn. O registo das ligações SSE e o ciclo de reconciliação estão em memória, e as 300
ligações SSE abertas ao mesmo tempo não pesaram (12 ligações à base, `/ready` abaixo de 50 ms). Mais processos só
depois de passar o SSE para `LISTEN/NOTIFY`.

## Por fazer

- **Repetir no staging.** No servidor o staging e a produção partilham a base de dados, e um teste de carga criaria
  contas, pagamentos e emails verdadeiros. Falta uma VPS ou base de staging separada para comparar com estes números.
- Medir o envio real de emails (o tempo por email do Resend) para saber o atraso da fila no fim do pico.
