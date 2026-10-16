# API de pagamentos

Contrato dos endpoints de bilheteira para quem desenvolve o frontend. O prefixo de todos os caminhos é `/api`. Os corpos dos pedidos e das respostas são JSON.

## Regras gerais

- **Sessão obrigatória (exceto no callback):** os endpoints de iniciar e consultar precisam do cookie de sessão (ver `api-auth.md`). Sem sessão a API responde `401`; com o email por verificar responde `403` com `Please verify your email address to continue.`. O `GET /payment/callback` é público porque é o ifthenpay que o chama.
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

> **Esta lista vai crescer.** É provável que a organização peça mais modalidades, por exemplo variantes **não estudante** com refeições e com a experiência completa (hoje só o passe geral é aberto a não estudantes). O frontend **não deve assumir que são sempre quatro**: nomes, preços e a marca de estudante não devem ficar espalhados pelo código, e um valor de `ticket_tier` desconhecido tem de falhar com graça. Acrescentar uma modalidade exige no backend um valor novo em `TicketTier`, a entrada em `TIER_SPECS`, uma migration (a coluna tem uma restrição com a lista dos valores e a linha de preço tem de ser criada) e o preço com `set_price`. Hoje não há endpoint que liste as modalidades; se o frontend precisar de uma lista dinâmica, pede-se um (por exemplo `GET /api/payment/tiers`).

O estado de estudante é decidido **pelo backend**, a partir do domínio do email do utilizador (`STUDENT_EMAIL_DOMAINS`). As modalidades de estudante só estão disponíveis para contas com `student_verification_status: "verified"`; as restantes recebem `403`.

## Endpoints

### `POST /api/payment/initiate`

Inicia um pagamento MB WAY e devolve a referência a mostrar ao utilizador. O bilhete é reservado durante alguns minutos (por omissão 4, `MBWAY_PAYMENT_TIMEOUT_SECONDS`); se o pagamento não for confirmado nesse tempo, a transação expira e o lugar volta a ficar livre.

| | |
| --- | --- |
| Corpo | `ticket_tier`, `phone`, `email` (opcional), `quantity` (opcional, tem de ser `1`) |
| `ticket_tier` | um de `acesso`, `refeicoes`, `completo`, `geral` |
| `phone` | telemóvel português. Aceita espaços e o indicativo (`912 345 678`, `+351 912345678`, `00351912345678`); é normalizado e guardado como `912345678` |
| `email` | se faltar, usa o email da conta |
| `quantity` | fixo em `1`: um bilhete por pessoa |
| `201` | ver o exemplo abaixo |
| `401` | sem sessão |
| `403` | email por verificar, ou modalidade de estudante sem verificação de estudante |
| `409` | modalidade esgotada (`This ticket tier is sold out`), ou a pessoa já tem bilhete ou um pagamento em curso (`You already have a ticket or a payment in progress`; um bilhete por pessoa, o pagamento em curso deixa de contar quando expira, falha ou é recusado) |
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

O callback é **idempotente**: confirmar a mesma referência duas vezes devolve `200` nas duas, sem duplicar o bilhete. Só confirma transações ainda `pending`: se a transação já estiver `failed` ou `expired`, responde `200` (para a ifthenpay parar de repetir) mas **não** altera o estado nem emite bilhete — deixa um aviso com a referência nos logs para tratamento manual. Se a pessoa **já tem um bilhete** de outro pagamento (um bilhete por pessoa, por exemplo porque pagou duas vezes), não se emite um segundo: a transação passa a `refund_due`, o log regista um erro `needs a refund` (ver `deploy.md`, «Pagamentos a reembolsar») e o callback responde `200` na mesma, para a ifthenpay parar de repetir. Ao confirmar, o backend marca a transação como `confirmed` e emite o bilhete com o QR assinado, estado e bilhete na mesma operação. A ifthenpay repete a chamada até receber `200`, por isso qualquer outro código é tratado como falha e volta a ser tentado.

A chave anti-phishing transita no *query string* do pedido; o backend remove-a dos logs de acesso do uvicorn e o nginx já esconde o caminho `/api/payment/callback`.

## Estados de uma transação

| `status` | Significado |
| --- | --- |
| `pending` | à espera que o utilizador confirme no MB WAY (ou a ser confirmado) |
| `confirmed` | pago |
| `failed` | o gateway recusou ou falhou |
| `expired` | passou o prazo sem confirmação |
| `refund_due` | o dinheiro chegou mas não há bilhete para dar (a pessoa já tem um, ou a modalidade esgotou): vai ser reembolsado. Não ocupa stock |

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
| Fecha o browser e **não aprova** | A transação continua `pending` até passar o prazo (4 minutos); a primeira consulta depois disso devolve (e grava) `expired`. | Pode comprar outra vez. |
| Volta antes de o prazo acabar e tenta comprar outra vez | `POST /payment/initiate` responde `409` com `You already have a ticket or a payment in progress`: o pagamento em curso conta como a compra dessa pessoa até confirmar, falhar ou expirar. | Ir para o ecrã de espera com a referência guardada (ver abaixo); se não houver referência, mostrar «Tens um pagamento em curso, tenta daqui a uns minutos» e consultar `/users/me`. |
| Aprova depois de a transação já estar `expired` ou `failed` | O callback responde `200` mas **não** emite bilhete (fica um aviso nos logs para tratamento manual, normalmente reembolso). O ifthenpay não deixa aprovar depois dos 4 minutos, por isso é raro. | — |

Hoje não existe um endpoint que devolva a referência do pagamento em curso. Até haver (está planeado), o frontend deve **guardar a `reference` no `sessionStorage`** logo que recebe o `201` e, ao abrir o ecrã de espera, consultar `GET /payment/transactions/{reference}` com ela. Sem a referência (outro dispositivo, armazenamento limpo), resta o `409` acima e esperar que o prazo passe.

## Modos de pagamento (`PAYMENTS_MODE`)

O modo é explícito e não depende do que estiver (ou não) configurado:

| `PAYMENTS_MODE` | Comportamento |
| --- | --- |
| `off` (por omissão) | a bilheteira não vende: `/payment/initiate` responde `503`. |
| `simulated` | cria a transação e responde sempre `pending`, sem contactar nenhum serviço externo. É o modo usado em desenvolvimento e em *staging* para construir o fluxo completo (espera, timeout e erro) com respostas reais da API. |
| `live` | usa o gateway ifthenpay real. Exige `MBWAY_KEY`, um `MBWAY_BASE_URL` em `https` e a chave `MBWAY_CALLBACK_KEY`; sem eles o backend recusa arrancar. |

- Para testar o ecrã de sucesso sem um gateway real, usa-se `PAYMENTS_MODE=simulated` com `PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS` > 0: o pagamento passa a `confirmed` ao fim desses segundos (ver abaixo). O modo de confirmação só é permitido com `PAYMENTS_MODE=simulated`; com `live` ou `off` o backend recusa arrancar.
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
| `PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS` | `0` | o gateway simulado confirma o pagamento ao fim destes segundos (`0` = nunca). Só é permitido com `PAYMENTS_MODE=simulated`; com `live` ou `off` o backend recusa arrancar. |
| `RATE_LIMIT_PAYMENT_PER_MINUTE` | `10` | pedidos de `/initiate` por minuto por utilizador |
| `RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE` | `120` | consultas de `/transactions/{reference}` por minuto por utilizador (o frontend faz *polling*) |

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
| `403` com `Student verification is required to buy this ticket` | modalidade de estudante sem verificação | «Esta modalidade é para estudantes com a conta verificada.» | Sugerir o passe geral ou o contacto da organização |
| `409` com `This ticket tier is sold out` | modalidade esgotada | «Esta modalidade esgotou.» | Voltar à escolha de modalidade |
| `409` com `You already have a ticket or a payment in progress` | já tem bilhete ou pagamento em curso | «Já tens um bilhete ou um pagamento em curso.» (**não** dizer «esgotado») | Se `/users/me` tem `qr_code`, mostrar o bilhete; senão, ir para o ecrã de espera com a referência guardada |
| `422` | telemóvel, modalidade ou quantidade inválidos | Erro junto ao campo (normalmente o telemóvel) | Deixar corrigir e reenviar |
| `429` | mais de 10 pedidos por minuto | «Demasiadas tentativas. Tenta daqui a alguns segundos.» | Desativar o botão durante `Retry-After` segundos (cabeçalho da resposta) |
| `502` | o MB WAY falhou; a transação fica `failed` | «Não conseguimos iniciar o pagamento. Tenta outra vez.» | Deixar tentar logo: uma transação `failed` não conta como pagamento em curso |
| `503` com `Ticket sales are not open yet` | modalidade ainda sem preço | «A bilheteira ainda não abriu.» | Sem repetição automática |
| `503` com `Payments are currently disabled.` | `PAYMENTS_MODE=off` | «Os pagamentos estão temporariamente indisponíveis.» | Sem repetição automática |
| Sem resposta (rede ou 5xx) | falha de ligação | «Sem ligação. Verifica a rede e tenta outra vez.» | **Não** repetir sozinho: o pedido pode ter chegado e há um pagamento em curso; deixar a pessoa tentar, e um `409` leva ao ecrã de espera |

O `409` tem o mesmo código nos dois casos: distingue-se pelo `detail`, que é exatamente um dos dois textos da tabela.
