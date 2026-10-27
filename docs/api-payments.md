# API de pagamentos

Contrato dos endpoints de bilheteira para quem desenvolve o frontend. O prefixo de todos os caminhos é `/api`. Os corpos dos pedidos e das respostas são JSON.

## Regras gerais

- **Sessão obrigatória (exceto no callback e no webhook do Stripe):** os endpoints de iniciar e consultar precisam do cookie de sessão (ver `api-auth.md`). Sem sessão a API responde `401`; com o email por verificar responde `403` com `Please verify your email address to continue.`. O `GET /payment/callback` (ifthenpay) e o `POST /payment/stripe/webhook` são públicos porque é o fornecedor que os chama; cada um tem a sua própria autenticação (chave anti-phishing e assinatura do corpo).
- **O preço é sempre do servidor.** O frontend escolhe a modalidade (`ticket_tier`); nunca envia o preço. A quantidade é sempre `1` (um bilhete por pessoa): pode ser omitida no pedido e vem sempre como `1` na resposta. Assim ninguém consegue pagar 1 cêntimo por um bilhete.
- **Referência curta:** cada pagamento tem uma referência no formato `ENEI-XXXXXXXXXX` (15 caracteres no máximo, como no design). É esse valor que o frontend mostra e usa para consultar o estado.
- **Dinheiro em cêntimos:** todos os valores são inteiros, em cêntimos de euro (por exemplo `4500` são `45,00 €`).
- **Acesso aos próprios pagamentos:** só o dono do pagamento o consegue consultar; para qualquer outro utilizador a referência não existe (`404`).

## Modalidades de bilhete

| `ticket_tier` | Nome | Estudante |
| --- | --- | --- |
| `acesso` | Apenas acesso | sim |
| `refeicoes` | Acesso + refeições | sim |
| `completo` | Experiência completa | sim |
| `geral` | Passe geral | não |
| `geral_refeicoes` | Passe geral + refeições | não |

> **Esta lista vai crescer.** É provável que a organização peça mais modalidades, por exemplo outras variantes **não estudante** (hoje há o passe geral e o passe geral com refeições). O frontend **não deve assumir que são sempre cinco**: nomes, preços e a marca de estudante não devem ficar espalhados pelo código, e um valor de `ticket_tier` desconhecido tem de falhar com graça. Acrescentar uma modalidade exige no backend um valor novo em `TicketTier`, a entrada em `TIER_SPECS`, uma migration (a coluna tem uma restrição com a lista dos valores e a linha de preço tem de ser criada) e o preço com `set_price`. As modalidades e os preços lêem-se em `GET /api/payment/tiers`.

O estado de estudante é decidido **pelo backend**, a partir do domínio do email do utilizador (`STUDENT_EMAIL_DOMAINS`) ou, para quem não tem email de aluno, do comprovativo de matrícula (`POST /api/users/me/student-proof`, ver `docs/api-auth.md`). As modalidades de estudante só estão disponíveis para contas com `student_verification_status: "verified"`; as restantes recebem `403`.

## Endpoints

### `GET /api/payment/tiers`

**Público** (sem sessão): as modalidades, com o preço e se cada uma se pode comprar agora. É o que o checkout e a página de Bilhetes usam para mostrar preços e «esgotado». Limite de 60 pedidos por minuto por IP (`RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE`); `Cache-Control: no-store`.

```json
[
  {
    "tier": "geral",
    "name": "Passe geral",
    "price_cents": 5000,
    "currency": "EUR",
    "is_student": false,
    "sale_open": true,
    "available": true
  }
]
```

| Campo | Significado |
| --- | --- |
| `price_cents` | preço em cêntimos; `null` se a modalidade ainda não tem preço |
| `is_student` | só quem tem a verificação de estudante a pode comprar |
| `sale_open` | `false` enquanto os pagamentos estão desligados (`PAYMENTS_MODE=off`) ou a modalidade não tem preço |
| `available` | `false` se não é possível comprar agora: bilheteira fechada, ou todos os lugares estão ocupados **ou reservados** para um pagamento que espera |

Não se mostra quantos lugares restam. A ordem é fixa (acesso, refeições, completo, geral) e a lista pode crescer: a Frontend não deve assumir que são quatro.

### `POST /api/payment/initiate`

Inicia um pagamento MB WAY e devolve a referência a mostrar ao utilizador. **O lugar fica reservado enquanto o pagamento espera**, como numa loja: a pessoa tem alguns minutos para aprovar (por omissão 4, `MBWAY_PAYMENT_TIMEOUT_SECONDS`, que é o `expires_at`), mas o lugar só se liberta quando o MB WAY diz que o pagamento terminou (pago, recusado ou expirado), não quando o prazo passa. Para a pessoa seguinte, os lugares reservados contam como ocupados: com 2 bilhetes e 2 pessoas no checkout, a terceira recebe `409` «esgotado». Quando uma modalidade parece esgotada, o backend pergunta primeiro ao MB WAY pelos pagamentos com o prazo já ultrapassado (os abandonados) e liberta os que já terminaram. Se a pessoa já tem um pagamento anterior à espera, o novo pedido pergunta ao MB WAY por ele antes de decidir.

| | |
| --- | --- |
| Corpo | `ticket_tier`, `phone`, `email` (opcional), `nif` (opcional), `quantity` (opcional, tem de ser `1`) |
| `ticket_tier` | um de `acesso`, `refeicoes`, `completo`, `geral`, `geral_refeicoes` |
| `phone` | telemóvel português. Aceita espaços e o indicativo (`912 345 678`, `+351 912345678`, `00351912345678`); é normalizado e guardado como `912345678` |
| `email` | se faltar, usa o email da conta |
| `nif` | opcional, para a fatura. Aceita espaços, pontos, hífenes e o prefixo `PT` (`123 456 789`, `PT123456789`); vazio ou em falta é aceite e fica sem NIF. Se vier preenchido tem de ter 9 algarismos (só `0-9`), um primeiro algarismo que exista (sem `0`, e o `4` só como `45`), no máximo 32 caracteres no total e o algarismo de controlo certo (módulo 11), senão `422` **e nenhum lugar fica reservado**. Guarda-se na transação (`transactions.nif`, 9 algarismos), **vive e morre com a transação, como o telemóvel** (não se apaga quando o pagamento falha ou expira; sai quando o registo da compra é removido) e **nunca é devolvido pela API**: nem em `/payment/initiate`, nem em `/payment/transactions/{reference}` |
| `quantity` | fixo em `1`: um bilhete por pessoa |
| `201` | ver o exemplo abaixo |
| `401` | sem sessão |
| `403` | email por verificar, ou modalidade de estudante sem verificação de estudante |
| `409` | modalidade esgotada (`This ticket tier is sold out`), ou a pessoa já tem bilhete ou um pagamento em curso (`You already have a ticket or a payment in progress`; um bilhete por pessoa, o pagamento em curso deixa de contar quando o MB WAY o dá por terminado: pago, recusado ou expirado) |
| `422` | corpo inválido (telemóvel, NIF, quantidade ou modalidade) |
| `429` | mais de 10 pedidos por minuto (`RATE_LIMIT_PAYMENT_PER_MINUTE`) |
| `502` | o gateway MB WAY falhou. A transação fica marcada como `failed`; o frontend pode pedir ao utilizador para tentar de novo. |
| `503` | bilheteira fechada (essa modalidade ainda sem preço) ou pagamentos desligados (`PAYMENTS_MODE=off`) |

Resposta `201`:

```json
{
  "reference": "ENEI-4F2A9C1D7B",
  "ticket_tier": "completo",
  "status": "pending",
  "amount_cents": 4500,
  "quantity": 1,
  "currency": "EUR",
  "phone": "912345678",
  "expires_at": "2026-10-09T10:04:32.935743+00:00",
  "confirmed_at": null,
  "created_at": "2026-10-09T10:00:32+00:00"
}
```

### `GET /api/payment/transactions/{reference}`

Consulta o estado de um pagamento. O frontend usa isto para fazer *polling* enquanto mostra o ecrã de espera do MB WAY.

| | |
| --- | --- |
| `200` | a mesma forma do `201` acima |
| `401` | sem sessão |
| `403` | email por verificar |
| `404` | referência inexistente ou de outro utilizador |

Enquanto o pagamento estiver `pending`, esta chamada pergunta primeiro ao fornecedor (MB WAY) qual o estado real e grava o resultado: se o fornecedor devolver `confirmed`, `failed` ou `expired`, a transação passa a esse estado (no caso de `confirmed` fica também gravado `confirmed_at` **e o bilhete é emitido**, pela mesma função que o callback usa). Se o fornecedor ainda responde `pending`, ou está inacessível, a transação **continua `pending` e com o lugar reservado, mesmo depois do prazo** (`expires_at`): só o MB WAY pode terminar um pagamento. O frontend deve tratar `pending` depois de `expires_at` como «ainda a confirmar» e não como erro. O backend pergunta ao MB WAY **no máximo uma vez por pagamento a cada 5 segundos** (`PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS`); entre duas perguntas devolve o estado guardado. Por isso o polling de 2 em 2 segundos é seguro, mas um pagamento pago só aparece como `confirmed` até 5 segundos depois se o callback não chegar (o callback confirma logo). Na prática o MB WAY dá o pagamento por expirado ao fim dos 4 minutos. Há uma exceção: se o MB WAY **não consegue dizer** (responde algo que não se lê, ou nunca guardámos a referência dele), o pagamento dá-se por expirado `MBWAY_UNRESOLVED_MAX_WAIT_SECONDS` (30 minutos) depois do prazo, com um erro no log, para não prender o lugar para sempre. Um MB WAY inacessível ou que responde «à espera» nunca provoca isto.

### `GET /api/payment/transactions/{reference}/events`

O estado do pagamento **em tempo real**, por Server-Sent Events (`text/event-stream`). É a alternativa a perguntar de 2 em 2 segundos: o browser abre **um só pedido** que fica aberto e o servidor avisa na hora em que o pagamento muda.

| | |
| --- | --- |
| Sessão | a mesma do resto (cookie), conta verificada. O browser (`EventSource`) envia-o sozinho |
| `401` / `404` | sem sessão / pagamento que não é seu (como a consulta) |
| `429` | demasiadas ligações abertas (`PAYMENT_EVENTS_MAX_PER_USER`, 3) ou limite de pedidos |
| Corpo | `retry: 3000`, depois `event: status` com `data: {"status": "..."}`: primeiro o estado atual e depois cada mudança; fecha quando o estado é final (`confirmed`, `failed`, `expired`, `refund_due`, `refunded`) |
| Batimento | uma linha `: keep-alive` de 15 em 15 segundos (`PAYMENT_EVENTS_HEARTBEAT_SECONDS`), para o nginx e o túnel não fecharem uma ligação calada |
| Duração | no máximo 10 minutos por ligação (`PAYMENT_EVENTS_MAX_SECONDS`): o browser reconecta sozinho e volta a receber o estado |
| Cabeçalhos | `Cache-Control: no-store`, `X-Accel-Buffering: no` |

O evento só **avisa** (`status`, sem dados pessoais): o frontend faz então uma consulta normal (`GET /payment/transactions/{reference}`) e trata o resultado como sempre, incluindo conferir a conta nos `failed` e `expired`. Se o fluxo falhar, o frontend volta a consultar de 2 em 2 segundos, por isso nunca depende dele.

**Como funciona no servidor.** Quem muda um pagamento (a confirmação, o callback, a libertação de um lugar, o cancelamento) avisa as ligações abertas desse pagamento. Como o backend corre **um só processo**, o registo das ligações está em memória; com mais de um processo seria preciso `LISTEN/NOTIFY` ou Redis. Uma ligação em espera **não ocupa nenhuma ligação à base de dados**. Um laço em segundo plano (`PAYMENT_EVENTS_RECONCILE_SECONDS`, 5 s) pergunta ao fornecedor pelos pagamentos que alguém está a ver, no máximo de 5 em 5 segundos por pagamento (`PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS`) e 4 de cada vez, para um fornecedor lento não ocupar as threads todas. O nginx trata este caminho à parte (`proxy_events.conf`: sem retenção nem compressão e com 120 s de espera).

### `POST /api/payment/stripe/webhook`

Endpoint público que o Stripe chama quando um pagamento termina. Não usa sessão: o corpo é autenticado pela **assinatura** do cabeçalho `Stripe-Signature` (HMAC-SHA256 do corpo bruto com `STRIPE_WEBHOOK_SECRET`, `whsec_…`), com uma tolerância de `STRIPE_WEBHOOK_TOLERANCE_SECONDS` (300 s) para trás e para a frente.

| Evento | O que faz |
| --- | --- |
| `payment_intent.succeeded` | confirma a transação e emite o bilhete, como o polling. Exige `currency=eur` e `amount_received` igual ao valor cobrado; senão **não confirma** e fica um erro no log (`needs a look`). Também confirma um pagamento que já tínhamos dado por `failed` ou `expired` (se houver lugar; senão fica `refund_due`) |
| `payment_intent.payment_failed` e `payment_intent.canceled` | terminam (`failed` ou `expired`, segundo o erro) um pagamento que ainda espera; nunca alteram um já confirmado |
| qualquer outro | `200` e nada acontece |

O pagamento identifica-se pela referência que pusemos nos metadados do *PaymentIntent* e só conta se for um pagamento nosso feito pelo Stripe com esse mesmo id (um evento que chegue antes de guardarmos o id também é aceite). Respostas: `200` (processado ou ignorado, para o Stripe parar de repetir), `400` (assinatura ou corpo inválidos), `429` (demasiadas assinaturas inválidas deste IP; as válidas nunca são contadas), `503` (`STRIPE_WEBHOOK_SECRET` por configurar) e `500` numa falha inesperada, que o Stripe repete. É idempotente.

**Registo no Stripe:** painel, Developers, Webhooks, endereço `https://<domínio>/api/payment/stripe/webhook`, eventos `payment_intent.succeeded`, `payment_intent.payment_failed` e `payment_intent.canceled`; o segredo `whsec_…` que o painel mostra vai para o Secret `STRIPE_WEBHOOK_SECRET`. Em desenvolvimento usa-se `stripe listen --forward-to localhost:8000/api/payment/stripe/webhook`, que gera o seu próprio `whsec_…`.

### `GET /api/payment/callback`

Endpoint público que a ifthenpay chama quando o pagamento MB WAY é concluído. Não usa sessão: a autenticidade é garantida pela **chave anti-phishing** (`MBWAY_CALLBACK_KEY`), que o ifthenpay devolve em cada chamada e que só o nosso backend conhece.

| Parâmetro | Descrição |
| --- | --- |
| `key` ou `apk` | chave anti-phishing configurada no backoffice da ifthenpay |
| `orderId` ou `oid` | a referência do pagamento (`ENEI-XXXXXXXXXX`) |
| `amount` ou `val` | valor pago, em euros (por exemplo `45.00`) |

O parâmetro `requestId` (ou `tid`) que a ifthenpay também envia é aceite mas ignorado. A resposta é sempre um JSON curto:

| | |
| --- | --- |
| `200` | `{"status": "ok"}` — pagamento confirmado (ou já confirmado antes) |
| `400` | valor em falta, não numérico ou diferente do que foi cobrado |
| `403` | chave anti-phishing ausente ou errada |
| `404` | referência desconhecida |
| `429` | mais de 60 pedidos por minuto do mesmo IP (`RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE`) |

O callback é **idempotente**: confirmar a mesma referência duas vezes devolve `200` nas duas, sem duplicar o bilhete. A ifthenpay só chama o callback quando o dinheiro foi pago, por isso o callback confirma a transação e emite o bilhete, também depois do prazo (o lugar continua reservado) e até se a transação tiver sido marcada `failed` ou `expired`, **se ainda houver lugar**. Como o lugar está reservado e uma pessoa só pode ter um pagamento à espera, o caso contrário não devia acontecer; se acontecer (um pagamento dado por terminado que afinal foi pago, com a modalidade esgotada entretanto, ou uma pessoa que já tem bilhete), o bilhete **não** se emite: a transação passa a `refund_due`, o log regista um erro `needs a refund` (ver `deploy.md`, «Pagamentos a reembolsar») e o callback responde `200` na mesma, para a ifthenpay parar de repetir. Um `refund_due` não volta a ser reavaliado. Ao confirmar, o backend marca a transação como `confirmed` e emite o bilhete com o QR assinado, tudo na mesma operação. A ifthenpay repete a chamada até receber `200`, por isso qualquer outro código é tratado como falha e volta a ser tentado.

A chave anti-phishing transita no *query string* do pedido; o backend remove-a dos logs de acesso do uvicorn e o nginx já esconde o caminho `/api/payment/callback`.

## Estados de uma transação

| `status` | Significado |
| --- | --- |
| `pending` | à espera que o utilizador confirme no MB WAY (ou a ser confirmado) |
| `confirmed` | pago |
| `failed` | o gateway recusou ou falhou |
| `expired` | o MB WAY deu o pagamento por terminado sem ser pago (normalmente aos 4 minutos), ou, no Stripe, o pagamento continuava à espera `STRIPE_CANCEL_GRACE_SECONDS` depois do prazo e foi cancelado |
| `refund_due` | o dinheiro chegou mas não há bilhete para dar (a pessoa já tem um, ou a modalidade esgotou depois de o pagamento ter sido dado por terminado): vai ser reembolsado. Não ocupa stock. Não devia acontecer |
| `refunded` | o dinheiro foi devolvido (`python -m app.domains.payments.refund`, ver `docs/deploy.md`) e, se havia bilhete deste pagamento, foi cancelado. **Liberta o lugar** e a pessoa pode comprar outra vez. Um callback repetido não o altera |

`failed` e `expired` quase nunca mudam, mas se o dinheiro chegar depois o callback confirma a transação e emite o bilhete (havendo lugar). Por isso, quando o polling devolve `expired` ou `failed`, antes de dizer à pessoa para tentar outra vez o frontend deve consultar `GET /api/users/me` (se `qr_code` já não for `null`, mostra o bilhete). Se mesmo assim tentar pagar outra vez, o `POST /payment/initiate` responde `409` («já tens bilhete») e a pessoa é levada ao bilhete. Com `refund_due`, mostra-se: «Recebemos o teu pagamento, mas já não há bilhetes (ou já tens um). Vamos reembolsar-te» e o contacto da organização.

Fluxo típico no frontend:

```js
const payment = await fetch("/api/payment/initiate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ ticket_tier: "completo", phone: "912345678" }),
}).then((r) => r.json());

// mostra payment.reference e faz polling até sair de "pending"
const timer = setInterval(async () => {
  const tx = await fetch(`/api/payment/transactions/${payment.reference}`).then(
    (r) => r.json(),
  );
  if (tx.status === "confirmed") finish(tx);
  if (tx.status === "failed" || tx.status === "expired") fail(tx);
}, 2000);
```

## Se a pessoa fecha o browser antes da confirmação

O pagamento não depende do browser: depois de `POST /payment/initiate` o pedido está no MB WAY e a pessoa aprova no telemóvel. O que acontece em cada caso:

| Situação | O que acontece | O que o frontend faz |
| --- | --- | --- |
| Fecha o browser e **aprova** no MB WAY | O ifthenpay chama o callback, a transação passa a `confirmed` e o bilhete é emitido, tenha ou não o site aberto. | Ao voltar a entrar, `GET /api/users/me` devolve o `qr_code` (deixa de ser `null`): mostrar o bilhete. |
| Fecha o browser e **não aprova** | A transação continua `pending` e o lugar reservado até o MB WAY a dar por terminada (normalmente ao fim dos 4 minutos). A próxima consulta, um novo pedido de compra da pessoa, ou o pedido de outra pessoa quando a modalidade parece esgotada, pergunta ao MB WAY e grava `expired`. | Pode comprar outra vez depois disso. |
| Volta e tenta comprar outra vez enquanto o pagamento anterior ainda espera | `POST /payment/initiate` pergunta ao MB WAY pelo pagamento anterior; se ele ainda espera, responde `409` com `You already have a ticket or a payment in progress`; se já terminou como pago, o `409` é por já ter bilhete; se terminou sem pagar, o novo pedido é aceite. | Ir para o ecrã de espera com a referência guardada (ver abaixo); se não houver referência, mostrar «Tens um pagamento em curso, tenta daqui a uns minutos» e consultar `/users/me`. |
| Aprova depois de a transação já estar `expired` ou `failed` | Não devia acontecer (o MB WAY não deixa aprovar depois de terminar). Se acontecer, o callback confirma-a e emite o bilhete **se ainda houver lugar**; se não, ou se a pessoa já tem bilhete, fica `refund_due` e é reembolsada. | Quem consulta a transação antiga vê `confirmed` (e o bilhete em `/users/me`) ou `refund_due`. |

Hoje não existe um endpoint que devolva a referência do pagamento em curso. Até haver (está planeado), o frontend deve **guardar a `reference` no `sessionStorage`** logo que recebe o `201` e, ao abrir o ecrã de espera, consultar `GET /payment/transactions/{reference}` com ela. Sem a referência (outro dispositivo, armazenamento limpo), resta o `409` acima e esperar que o prazo passe.

## Modos de pagamento (`PAYMENTS_MODE`)

O modo é explícito e não depende do que estiver (ou não) configurado:

| `PAYMENTS_MODE` | Comportamento |
| --- | --- |
| `off` (por omissão) | a bilheteira não vende: `/payment/initiate` responde `503`. |
| `simulated` | cria a transação e responde sempre `pending`, sem contactar nenhum serviço externo. É o modo usado em desenvolvimento e em *staging* para construir o fluxo completo (espera, timeout e erro) com respostas reais da API. |
| `live` | usa o gateway real escolhido por `PAYMENTS_PROVIDER`: **`stripe`** (por omissão) exige `STRIPE_SECRET_KEY` (`sk_...`) e `STRIPE_WEBHOOK_SECRET` (`whsec_...`); `ifthenpay` exige `MBWAY_KEY`, um `MBWAY_BASE_URL` em `https` e a chave `MBWAY_CALLBACK_KEY`. Sem as credenciais do gateway escolhido o backend recusa arrancar. |

- **Stripe (MB WAY):** o servidor cria e confirma um *PaymentIntent* com o telemóvel do nosso formulário (`+351` + 9 algarismos) e a pessoa aprova na app MB WAY, exatamente como com a ifthenpay: não há redirecionamento nem Stripe.js. A referência do fornecedor é o id do *PaymentIntent* (`pi_...`) e o estado lê-se com `GET /v1/payment_intents/{id}`: `succeeded` é `confirmed`, `requires_action` e `processing` são `pending`, `requires_payment_method` com o erro `payment_intent_payment_attempt_expired` é `expired` e com qualquer outro erro (recusa da pessoa ou do MB WAY) é `failed`, `canceled` é `failed`. Um estado que não se reconhece é erro e não espera. Cada pagamento usa a chave de idempotência `enei-<referência>`, por isso um pedido repetido não cria uma segunda cobrança, e a referência do pagamento vai nos metadados. A descrição do pagamento é `ENEI - <nome da modalidade>` (por exemplo `ENEI - Passe geral`), porque a conta do Stripe é partilhada com outros eventos e cada cobrança tem de dizer de que evento e produto é. O reembolso leva o mesmo texto em `metadata[description]` (um reembolso do Stripe não tem campo `description`, só metadados e um `reason` de valores fixos). O email da pessoa não é enviado ao Stripe. No sandbox, os telemóveis `911111112` (confirma ao fim de uns 30 s), `911111113`, `911111114`, `911111115` (expira) e `911111116` (recusa a pessoa) reproduzem cada caso.
- Para testar o ecrã de sucesso sem um gateway real, usa-se `PAYMENTS_MODE=simulated` com `PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS` > 0: o pagamento passa a `confirmed` ao fim desses segundos (ver abaixo). Com o telemóvel `910000000` o simulador nunca aprova o pagamento, que expira ao fim de `MBWAY_PAYMENT_TIMEOUT_SECONDS`: serve para ver o ecrã de pagamento expirado. O modo de confirmação só é permitido com `PAYMENTS_MODE=simulated`; com `live` ou `off` o backend recusa arrancar.
- Para testar o erro `502`, o frontend pode apontar um `MBWAY_BASE_URL` inválido em modo `live`.
- Em `prod` com `PAYMENTS_MODE=simulated` o backend registra um aviso no arranque: os pagamentos não são reais.

## Abrir a bilheteira

O preço de cada modalidade vive na tabela `ticket_tiers`. Enquanto `price_cents` for `NULL` a bilheteira está fechada e `/payment/initiate` responde `503` (o servidor decide o preço, por isso nunca há uma transação de valor zero). Para abrir (preço com IVA, em cêntimos, sempre maior que zero):

```bash
# dentro de backend/ (usa a DATABASE_URL/.env do ambiente)
python -m app.domains.payments.set_price geral 3500
python -m app.domains.payments.set_price acesso 2500 --stock 150
# ou
make set-price tier=geral price=3500
```

`--stock` é opcional: define o limite de inventário (omisso = ilimitado); sem ele, o stock atual mantém-se.

## Configuração (backend)

| Variável | Por omissão | Descrição |
| --- | --- | --- |
| `STUDENT_EMAIL_DOMAINS` | vazio | domínios de email institucional que verificam o estudante automaticamente (lista separada por vírgulas) |
| `PAYMENTS_MODE` | `off` | `off`, `simulated` ou `live` (ver acima) |
| `PAYMENTS_PROVIDER` | `stripe` | gateway usado em `PAYMENTS_MODE=live`: `stripe` ou `ifthenpay` |
| `STRIPE_SECRET_KEY` | vazio | chave secreta do Stripe (`sk_test_...` no sandbox, `sk_live_...` em produção). Obrigatória com `PAYMENTS_MODE=live` e `PAYMENTS_PROVIDER=stripe`. Nunca vai para o git nem para os logs. |
| `STRIPE_WEBHOOK_SECRET` | vazio | segredo de assinatura do webhook (`whsec_...`). Obrigatório com `PAYMENTS_MODE=live` e `PAYMENTS_PROVIDER=stripe`. |
| `STRIPE_WEBHOOK_TOLERANCE_SECONDS` | `300` | diferença máxima entre a hora da assinatura e a atual |
| `STRIPE_API_VERSION` | `2026-08-26.dahlia` | versão da API do Stripe fixada em cada pedido, para uma versão nova não mudar o comportamento sem o decidirmos |
| `MBWAY_KEY` | vazio | chave MB WAY da ifthenpay. Obrigatória em `PAYMENTS_MODE=live`. |
| `MBWAY_BASE_URL` | `https://api.ifthenpay.com/spg/payment/mbway` | endpoint REST da ifthenpay. Em `live` tem de ser `https`. |
| `MBWAY_AUTH_TOKEN` | vazio | token de autenticação, se a conta o exigir |
| `MBWAY_CALLBACK_KEY` | vazio | chave anti-phishing do callback da ifthenpay. Obrigatória em `PAYMENTS_MODE=live`. |
| `MBWAY_TIMEOUT_SECONDS` | `10` | tempo máximo de espera do gateway |
| `MBWAY_PAYMENT_TIMEOUT_SECONDS` | `240` | prazo para a pessoa aprovar o pagamento (4 minutos). É o `expires_at`; não é o momento em que o lugar se liberta. No modo `simulated` é também quando o simulador dá o pagamento por expirado |
| `MBWAY_UNRESOLVED_MAX_WAIT_SECONDS` | `1800` | quanto tempo depois do prazo um pagamento que o MB WAY não consegue resolver (resposta ilegível ou sem referência) mantém o lugar antes de ser dado por expirado |
| `STRIPE_CANCEL_GRACE_SECONDS` | `120` | só Stripe: quanto tempo depois do prazo um pagamento ainda à espera é cancelado no Stripe (`POST /v1/payment_intents/{id}/cancel`), o que liberta o lugar e impede uma aprovação tardia. Se a pessoa o aprovar nesse instante, fica `confirmed`. Tem de ficar acima da janela real de aprovação do MB WAY |
| `PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS` | `5` | no máximo uma pergunta ao MB WAY por pagamento neste intervalo (0 = sempre). A memória é por processo; o backend corre um |
| `PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS` | `0` | o gateway simulado confirma o pagamento ao fim destes segundos (`0` = nunca). Só é permitido com `PAYMENTS_MODE=simulated`; com `live` ou `off` o backend recusa arrancar. |
| `RATE_LIMIT_PAYMENT_PER_MINUTE` | `10` | pedidos de `/initiate` por minuto por utilizador |
| `RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE` | `120` | consultas de `/transactions/{reference}` por minuto por utilizador (o frontend faz *polling*) |
| `RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE` | `60` | consultas de `GET /tiers` por minuto por IP |

Os preços ficam guardados na tabela `ticket_tiers` e são alterados em runtime com o comando `set_price` (ver "Abrir a bilheteira"). A migração cria as quatro modalidades com `price_cents` a `NULL`, ou seja, de bilheteira fechada.

## Erros comuns

| Código | Corpo |
| --- | --- |
| `401` | `{"detail": "..."}` (ver `api-auth.md`) |
| `403` | `{"detail": "Please verify your email address to continue."}` ou `{"detail": "Student verification is required to buy this ticket"}` |
| `409` | `{"detail": "This ticket tier is sold out"}` ou `{"detail": "You already have a ticket or a payment in progress"}` |
| `422` | `{"detail": [{"type", "loc", "msg"}]}` |
| `502` | `{"detail": "Payment could not be initiated. Please try again."}` |
| `503` | `{"detail": "Ticket sales are not open yet"}` ou `{"detail": "Payments are currently disabled."}` |

## O que o frontend mostra em cada erro do `/payment/initiate`

Os textos de `detail` estão em inglês e são para os logs e para distinguir casos; **o frontend mostra o seu próprio texto em português**. Os textos abaixo são a proposta.

| Código | Quando | O que mostrar | O que fazer |
| --- | --- | --- | --- |
| `401` | sem sessão ou sessão expirada | «A tua sessão terminou. Entra outra vez para continuar.» | Levar ao login e voltar ao checkout |
| `403` com `Please verify your email address to continue.` | email por verificar | «Confirma o teu email para poderes comprar.» | Oferecer reenviar o email de verificação |
| `403` com `Student verification is required to buy this ticket` | modalidade de estudante sem verificação | «Esta modalidade é só para estudantes com a conta verificada. Envia o comprovativo de matrícula ou escolhe outra modalidade.» | Ligação ao comprovativo no perfil (`/perfil#comprovativo`) e o contacto da organização (`geral@enei.pt`) |
| `409` com `This ticket tier is sold out` | modalidade esgotada | «Esta modalidade esgotou.» | Voltar à escolha de modalidade |
| `409` com `You already have a ticket or a payment in progress` | já tem bilhete ou pagamento em curso | «Já tens um bilhete ou um pagamento em curso.» (**não** dizer «esgotado») | Se `/users/me` tem `qr_code`, mostrar o bilhete; senão, ir para o ecrã de espera com a referência guardada |
| `422` | telemóvel, NIF, modalidade ou quantidade inválidos | Erro junto ao campo (o telemóvel ou o NIF; `loc` diz qual) | Deixar corrigir e reenviar |
| `429` | mais de 10 pedidos por minuto | «Demasiadas tentativas. Tenta daqui a alguns segundos.» | Desativar o botão durante `Retry-After` segundos (cabeçalho da resposta) |
| `502` | o MB WAY falhou; a transação fica `failed` | «Não conseguimos iniciar o pagamento. Tenta outra vez.» | Deixar tentar logo: uma transação `failed` não conta como pagamento em curso |
| `503` com `Ticket sales are not open yet` | modalidade ainda sem preço | «A bilheteira ainda não abriu.» | Sem repetição automática |
| `503` com `Payments are currently disabled.` | `PAYMENTS_MODE=off` | «Os pagamentos estão temporariamente indisponíveis.» | Sem repetição automática |
| Sem resposta (rede ou 5xx) | falha de ligação | «Sem ligação. Verifica a rede e tenta outra vez.» | **Não** repetir sozinho: o pedido pode ter chegado e há um pagamento em curso; deixar a pessoa tentar, e um `409` leva ao ecrã de espera |

O `409` tem o mesmo código nos dois casos: distingue-se pelo `detail`, que é exatamente um dos dois textos da tabela.
