# API de pagamentos

Contrato dos endpoints de bilheteira para quem desenvolve o frontend. O prefixo de todos os caminhos é `/api`. Os corpos dos pedidos e das respostas são JSON.

## Regras gerais

- **Sessão obrigatória (exceto no callback):** os endpoints de iniciar e consultar precisam do cookie de sessão (ver `api-auth.md`). Sem sessão a API responde `401`; com o email por verificar responde `403` com `Please verify your email address to continue.`. O `GET /payment/callback` é público porque é o ifthenpay que o chama.
- **O preço é sempre do servidor.** O frontend escolhe a modalidade (`ticket_tier`) e a quantidade; nunca envia o preço. Assim ninguém consegue pagar 1 cêntimo por um bilhete.
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

O estado de estudante é decidido **pelo backend**, a partir do domínio do email do utilizador (`STUDENT_EMAIL_DOMAINS`). As modalidades de estudante só estão disponíveis para contas com `student_verification_status: "verified"`; as restantes recebem `403`.

## Endpoints

### `POST /api/payment/initiate`

Inicia um pagamento MB WAY e devolve a referência a mostrar ao utilizador. O bilhete é reservado durante alguns minutos (por omissão 4, `MBWAY_PAYMENT_TIMEOUT_SECONDS`); se o pagamento não for confirmado nesse tempo, a transação expira e o lugar volta a ficar livre.

| | |
| --- | --- |
| Corpo | `ticket_tier`, `phone`, `email` (opcional), `quantity` (opcional, por omissão `1`) |
| `ticket_tier` | um de `acesso`, `refeicoes`, `completo`, `geral` |
| `phone` | telemóvel português. Aceita espaços e o indicativo (`912 345 678`, `+351 912345678`, `00351912345678`); é normalizado e guardado como `912345678` |
| `email` | se faltar, usa o email da conta |
| `quantity` | inteiro entre 1 e 10 |
| `201` | ver o exemplo abaixo |
| `401` | sem sessão |
| `403` | email por verificar, ou modalidade de estudante sem verificação de estudante |
| `409` | modalidade esgotada (`This ticket tier is sold out`) |
| `422` | corpo inválido (telemóvel, quantidade ou modalidade) |
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

Enquanto o pagamento estiver `pending`, esta chamada pergunta primeiro ao fornecedor (MB WAY) qual o estado real e grava o resultado: se o fornecedor devolver `confirmed`, `failed` ou `expired`, a transação passa a esse estado (no caso de `confirmed` fica também gravado `confirmed_at` **e o bilhete é emitido**, pela mesma função que o callback usa). Só quando o fornecedor ainda responde `pending` é que o prazo local decide: se já tiver passado, a chamada devolve (e grava) o estado `expired`. Se o fornecedor estiver temporariamente inacessível, a API mantém o estado atual para o *polling* não falhar.

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

O callback é **idempotente**: confirmar a mesma referência duas vezes devolve `200` nas duas, sem duplicar o bilhete. Só confirma transações ainda `pending`: se a transação já estiver `failed` ou `expired`, responde `200` (para a ifthenpay parar de repetir) mas **não** altera o estado nem emite bilhete — deixa um aviso com a referência nos logs para tratamento manual. Ao confirmar, o backend marca a transação como `confirmed` e emite o bilhete com o QR assinado. A ifthenpay repete a chamada até receber `200`, por isso qualquer outro código é tratado como falha e volta a ser tentado.

A chave anti-phishing transita no *query string* do pedido; o backend remove-a dos logs de acesso do uvicorn e o nginx já esconde o caminho `/api/payment/callback`.

## Estados de uma transação

| `status` | Significado |
| --- | --- |
| `pending` | à espera que o utilizador confirme no MB WAY (ou a ser confirmado) |
| `confirmed` | pago |
| `failed` | o gateway recusou ou falhou |
| `expired` | passou o prazo sem confirmação |

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

## Modos de pagamento (`PAYMENTS_MODE`)

O modo é explícito e não depende do que estiver (ou não) configurado:

| `PAYMENTS_MODE` | Comportamento |
| --- | --- |
| `off` (por omissão) | a bilheteira não vende: `/payment/initiate` responde `503`. |
| `simulated` | cria a transação e responde sempre `pending`, sem contactar nenhum serviço externo. É o modo usado em desenvolvimento e em *staging* para construir o fluxo completo (espera, timeout e erro) com respostas reais da API. |
| `live` | usa o gateway ifthenpay real. Exige `MBWAY_KEY`, um `MBWAY_BASE_URL` em `https` e a chave `MBWAY_CALLBACK_KEY`; sem eles o backend recusa arrancar. |

- Para testar o ecrã de sucesso é preciso `PAYMENTS_MODE=live` com um gateway real; o gateway simulado nunca devolve `confirmed`, exatamente para não confundir testes.
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
| `MBWAY_KEY` | vazio | chave MB WAY da ifthenpay. Obrigatória em `PAYMENTS_MODE=live`. |
| `MBWAY_BASE_URL` | `https://api.ifthenpay.com/spg/payment/mbway` | endpoint REST da ifthenpay. Em `live` tem de ser `https`. |
| `MBWAY_AUTH_TOKEN` | vazio | token de autenticação, se a conta o exigir |
| `MBWAY_CALLBACK_KEY` | vazio | chave anti-phishing do callback da ifthenpay. Obrigatória em `PAYMENTS_MODE=live`. |
| `MBWAY_TIMEOUT_SECONDS` | `10` | tempo máximo de espera do gateway |
| `MBWAY_PAYMENT_TIMEOUT_SECONDS` | `240` | validade do pagamento pendente (4 minutos) |
| `RATE_LIMIT_PAYMENT_PER_MINUTE` | `10` | pedidos de `/initiate` por minuto por utilizador |

Os preços ficam guardados na tabela `ticket_tiers` e são alterados em runtime com o comando `set_price` (ver "Abrir a bilheteira"). A migração cria as quatro modalidades com `price_cents` a `NULL`, ou seja, de bilheteira fechada.

## Erros comuns

| Código | Corpo |
| --- | --- |
| `401` | `{"detail": "..."}` (ver `api-auth.md`) |
| `403` | `{"detail": "Please verify your email address to continue."}` ou `{"detail": "Student verification is required to buy this ticket"}` |
| `409` | `{"detail": "This ticket tier is sold out"}` |
| `422` | `{"detail": [{"type", "loc", "msg"}]}` |
| `502` | `{"detail": "Payment could not be initiated. Please try again."}` |
| `503` | `{"detail": "Ticket sales are not open yet"}` ou `{"detail": "Payments are currently disabled."}` |
