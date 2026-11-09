# Emails do ENEI 2027

Quatro emails, cada um em HTML e em texto simples, com marcadores `[ASSIM]` que o backend substitui ao enviar.

| Email | HTML | Texto | Marcadores |
| --- | --- | --- | --- |
| Bilhete | `enei-ticket-confirmation-email.html` | `.txt` | `[FIRST_NAME]` `[ATTENDEE_NAME]` `[TICKET_TYPE]` `[TICKET_REFERENCE]` `[EVENT_DATES]` `[EVENT_LOCATION]` `[TICKET_URL]` |
| Verificação | `enei-verification-email.html` | `.txt` | `[FIRST_NAME]` `[VERIFICATION_URL]` `[VERIFICATION_VALIDITY_MINUTES]` |
| Recuperação | `enei-password-reset-email.html` | `.txt` | `[FIRST_NAME]` `[PASSWORD_RESET_URL]` `[RESET_VALIDITY_MINUTES]` |
| Palavra-passe alterada | `enei-password-changed-email.html` | `.txt` | `[FIRST_NAME]` `[PASSWORD_RESET_REQUEST_URL]` |

- O QR do bilhete é `<img src="cid:ticket-qr">` (240 px), anexado pelo backend (`TICKET_QR_CID`).
- Os minutos de validade vêm da configuração (`JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`); não escrever números fixos nos textos.
- Os valores substituídos no HTML têm de passar por `html.escape`; no texto simples vão tal e qual.
- Layout em tabelas, CSS em linha, 600 px, sem imagens de fundo, cores sólidas. `backend/tests/test_email_designs.py` falha se o desenho voltar a depender do que os clientes de email não suportam, se o HTML e o texto tiverem marcadores diferentes ou se aparecer uma cor fora da paleta validada (contraste de pelo menos 4,5:1).
- Esta pasta está em `.prettierignore`: o Prettier reescreve o CSS em linha e partiria os testes.
