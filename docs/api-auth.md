# API de autenticação

Contrato dos endpoints de autenticação para quem desenvolve o frontend. O prefixo de todos os caminhos é `/api`. Os
corpos dos pedidos e das respostas são JSON.

## Regras gerais

- **Sessão:** o login devolve o cookie `__Host-access_token` (`HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem
  `Domain`). O JavaScript não o consegue ler. Para saber se há sessão, chama `GET /api/auth/me`. Nunca leias nem
  escrevas o cookie à mão.
- **Quando a sessão termina:** ao expirar (60 minutos, ou 7 dias com `remember_me`, por omissão), no logout desse
  dispositivo, e em todos os outros dispositivos quando a password é mudada ou reposta. Nesses casos a API responde`401`
  e o frontend deve levar o utilizador ao login.
- **O site e a API ficam no mesmo endereço** (`/api/...` no mesmo domínio do site). Por isso usa caminhos relativos
  (`fetch('/api/auth/me')`), o browser envia o cookie sozinho e não há CORS. Só se a API estiver noutro endereço é que é
  preciso `credentials: 'include'` (e a origem do site tem de estar em `CORS_ALLOW_ORIGINS`).
- **Em desenvolvimento**, o cookie é `Secure`. Para testar o login no browser, abre o site completo em
  `http://localhost:8080` (ver o README da raiz); o Edge aceita cookies `Secure` em `localhost` (testado; o Chrome usa o
  mesmo motor, e o Firefox não foi testado). O `npm run dev` (porta 5173) é outro endereço e não encaminha `/api`.
- **Cache:** as respostas de `/api/auth/*` levam `Cache-Control: no-store`.
- **Erros:** quase todos têm o formato `{"detail": "mensagem"}`. Os erros de validação (422) têm uma lista (ver abaixo).

## Endpoints

### `POST /api/auth/register`

Cria uma conta e envia o email de verificação. Se o email já foi registado mas **nunca foi verificado**, a conta passa
para quem se regista agora (novo nome, nova password e novo email de verificação) e a resposta é igual à de uma conta
nova. Uma conta já verificada nunca é substituída.

|          |                                                                                                                                                                                                                           |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Corpo    | `name`, `email`, `password`, `accept_terms`                                                                                                                                                                               |
| Nome     | 1 a 255 caracteres, cortado nas pontas, com pelo menos uma letra. Sem caracteres de controlo, invisíveis (por exemplo zero-width), `<` ou `>`.                                                                            |
| Email    | só caracteres ASCII. É guardado em minúsculas (`Ana@Example.com` e `ana@example.com` são a mesma conta).                                                                                                                  |
| Password | 8 a 200 caracteres, com pelo menos uma maiúscula, um dígito e um símbolo, e no máximo 72 bytes. Um símbolo é **qualquer carácter que não seja `A-Z`, `a-z` ou `0-9`**: o espaço e as letras com acento (`é`, `ç`) contam. |
| Termos   | `accept_terms`: booleano obrigatório. Tem de ser explicitamente `true`. Rejeita com `422` se for `false` ou omitido.                                                                                                      |
| `201`    | `{"id", "name", "email", "role", "is_verified"}` (`role` é `user` ou `admin`)                                                                                                                                             |
| `409`    | `A user with this email already exists` (só se a conta já está verificada). Revela que o email já tem conta.                                                                                                              |
| `422`    | corpo inválido (ver os códigos abaixo)                                                                                                                                                                                    |
| `429`    | demasiados registos deste IP                                                                                                                                                                                              |

### `POST /api/auth/verify-email`

|       |                                                                                                                                                                                                                      |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Corpo | `token` (o `token` do link do email, que vale 30 minutos)                                                                                                                                                            |
| `200` | `{"message": "Email verified successfully"}` (também se a conta já estava verificada, desde que a password não tenha mudado desde o email)                                                                           |
| `400` | `Verification token has expired` ou `Invalid verification token`. O token está ligado à password da conta: se a conta foi substituída ou a password mudou, o link antigo deixa de funcionar e é preciso pedir outro. |
| `429` | demasiadas tentativas deste IP                                                                                                                                                                                       |

### `POST /api/auth/resend-verification-email`

|       |                                                                                                                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Corpo | `email`                                                                                                                                                                                                            |
| `200` | sempre `{"message": "If an account is awaiting verification, a verification email has been sent."}`, exista a conta ou não, e esteja verificada ou não (só envia email se a conta existir e estiver por verificar) |
| `429` | limite por email ou por IP                                                                                                                                                                                         |

### `POST /api/auth/login`

|       |                                                                                                                                              |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------|
| Corpo | `email` (não distingue maiúsculas), `password` (1 a 200 caracteres, sem as regras do registo), `remember_me` (opcional, por omissão `false`) |
| `200` | `{"message": "Login successful"}` e o cookie de sessão (60 minutos, ou 7 dias com `remember_me`)                                             |
| `401` | `Invalid email or password` (a mesma mensagem para email desconhecido, password errada e conta inativa)                                      |
| `403` | `Please verify your email address to continue.` (password certa, email por verificar)                                                        |
| `429` | demasiadas tentativas                                                                                                                        |

### `POST /api/auth/logout`

|       |                                                                                                                                                                                                                     |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `200` | `{"message": "Logout successful"}`, o cookie apagado no browser e o token revogado (mesmo que alguém o tenha copiado, deixa de funcionar). Só termina a sessão deste dispositivo. Responde `200` também sem sessão. |

### `GET /api/auth/me`

Precisa de sessão.

|       |                                                                                                                                                                                                                                                                                                                                            |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `200` | `{"id", "name", "email", "role", "is_verified"}`                                                                                                                                                                                                                                                                                           |
| `401` | qualquer problema com a sessão. O `detail` diz qual: `Not authenticated. Missing access token cookie.` (sem cookie), `Token has expired.`, `Invalid token.`, `Token has been revoked.` (sessão terminada), `User not found` (conta apagada) ou `Inactive user`. O frontend só precisa de olhar para o `401` e levar o utilizador ao login. |
| `403` | `Please verify your email address to continue.`                                                                                                                                                                                                                                                                                            |

### `POST /api/auth/forgot-password`

|       |                                                                                                                                      |
|-------|--------------------------------------------------------------------------------------------------------------------------------------|
| Corpo | `email`                                                                                                                              |
| `200` | sempre `{"message": "If the email exists in our system, you will receive a password recovery link shortly."}`, exista a conta ou não |
| `429` | limite por email ou por IP                                                                                                           |

O link do email de recuperação vale 15 minutos e só funciona uma vez. Pedir outro link não invalida o anterior, mas
assim que um dos links é usado, todos os outros deixam de funcionar. Também é enviado a contas que ainda não verificaram
o email.

### `PUT /api/auth/password`

Muda a password de quem tem sessão. Envia um email a avisar que a password mudou. **Termina as sessões dos outros
dispositivos**; este dispositivo continua com sessão, com um cookie novo que dura o que restava à sessão (no mínimo 1
minuto).

|       |                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------|
| Corpo | `current_password` (8 a 200 caracteres, sem as regras do registo), `new_password` (as regras do registo) |
| `200` | `{"message": "Password changed successfully"}`                                                           |
| `400` | `Your new password must be different from your current password`                                         |
| `401` | `Current password is incorrect`, ou sem sessão                                                           |
| `403` | email por verificar                                                                                      |
| `422` | `current_password` com menos de 8 caracteres, ou `new_password` que não cumpre as regras                 |
| `429` | 2 pedidos por 15 minutos (contam todos, certos ou errados)                                               |

### `POST /api/auth/reset-password`

Repõe a password com o `token` do email de recuperação. Envia um email a avisar que a password mudou. **Termina as
sessões de todos os dispositivos** e não inicia sessão: o utilizador tem de fazer login a seguir. Se a conta ainda não
estava verificada, **fica verificada** (o link chegou ao email dela).

|       |                                                                                                                                                                                       |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Corpo | `token` (1 a 2048 caracteres), `new_password` (as regras do registo)                                                                                                                  |
| `200` | `{"message": "Password reset successfully"}`                                                                                                                                          |
| `400` | `Password reset token has expired`, `Invalid password reset token`, `Password reset token has already been used`, ou `Your new password must be different from your current password` |
| `422` | corpo inválido                                                                                                                                                                        |
| `429` | demasiadas tentativas deste IP                                                                                                                                                        |

## Erros de validação (422)

Cada erro tem `type`, `loc` e `msg`. Nunca repete o valor enviado. Os erros do nome e da password trazem `ctx.rules` com
**todas** as regras de conteúdo que falharam, para o frontend mostrar mensagens claras:

```json
{
  "detail": [
    {
      "type": "password_invalid",
      "loc": [
        "body",
        "password"
      ],
      "msg": "Password does not meet the requirements",
      "ctx": {
        "rules": [
          "missing_uppercase",
          "missing_digit"
        ]
      }
    }
  ]
}
```

| `type`             | `ctx.rules` possíveis                                              |
|--------------------|--------------------------------------------------------------------|
| `password_invalid` | `too_long`, `missing_uppercase`, `missing_digit`, `missing_symbol` |
| `name_invalid`     | `blank`, `invalid_characters`, `no_letter`                         |
| `email_not_ascii`  | (sem `ctx`)                                                        |

O comprimento tem erros próprios, do pydantic, **sem `ctx`**: uma password com menos de 8 ou mais de 200 caracteres dá
`string_too_short` ou `string_too_long`, e só quando o comprimento está certo é que aparecem as regras de
`password_invalid` (por isso uma password curta nunca vem com `missing_uppercase` e semelhantes). O mesmo vale para o
nome (`string_too_long` acima de 255) e para `current_password`.

No campo `accept_terms`, se for omitido, o pydantic devolve o tipo `missing` (`Field required`). Se for enviado
explicitamente como `false`, devolve `value_error` com a mensagem
`"Value error, You must accept the terms and conditions"`. O resto são os tipos normais do pydantic (`missing`, ...).

## Respostas comuns

| Código | Quando                     | Corpo                                                                                                           |
|--------|----------------------------|-----------------------------------------------------------------------------------------------------------------|
| `413`  | corpo maior que 1 MB       | `{"detail": "Request body too large"}`                                                                          |
| `422`  | campo em falta ou inválido | `{"detail": [{"type", "loc", "msg"}]}`. Nunca repete o valor enviado.                                           |
| `429`  | limite de pedidos          | `{"detail": "Too many requests. Try again later."}` e o cabeçalho `Retry-After` (segundos)                      |
| `500`  | erro inesperado            | `{"detail": "Internal Server Error"}`                                                                           |
| `503`  | base de dados indisponível | `{"detail": "Service temporarily unavailable"}` (em `/api/health/ready` é `{"detail": "Database unavailable"}`) |

Mostra ao utilizador o tempo do `Retry-After` quando receberes um 429.

## Limites de pedidos

Cada limite é uma janela fixa que começa no primeiro pedido (a contagem recomeça quando a janela acaba), e os pedidos
bloqueados também contam. Os valores mudam com as variáveis `RATE_LIMIT_*` (ver o README do backend).

| Endpoint                                   | Limite                                                                     |
|--------------------------------------------|----------------------------------------------------------------------------|
| login                                      | 5 por minuto por email e IP, 20 por minuto por email, 30 por minuto por IP |
| register                                   | 2 por minuto por IP                                                        |
| resend-verification-email, forgot-password | 1 por minuto e 5 por hora por email, 10 por minuto por IP                  |
| PUT password                               | 2 por 15 minutos por utilizador                                            |
| verify-email, reset-password               | 20 por minuto por IP                                                       |

## Links dos emails

O email de verificação aponta para `{FRONTEND_URL}/conta/verificar?token=...` e o de recuperação para
`{FRONTEND_URL}/conta/redefinir?token=...`, que são os caminhos do design. **O frontend tem de ter estas duas páginas**:
lêem o `token` do endereço e chamam `verify-email` e `reset-password`. Os caminhos mudam com `FRONTEND_VERIFY_PATH` e
`FRONTEND_RESET_PATH`.

## Saúde

- `GET /api/health`: o processo está vivo (`{"status": "OK"}`, não toca na base de dados).
- `GET /api/health/ready`: a base de dados responde (`{"status": "OK"}`, ou `503` se não).
