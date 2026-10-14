# API de administração

Todas as rotas de administração vivem sob `/api/admin`. Exigem **sessão, email verificado e papel `admin`**. A regra está no próprio router (`app/domains/admin/router.py`, `dependencies=[Depends(get_current_admin)]`), por isso nenhuma rota nova do `/admin` pode esquecer-se dela.

| Pedido | Resposta |
| --- | --- |
| sem cookie de sessão, ou com sessão inválida, revogada ou de conta inativa | `401` |
| sessão válida, email por verificar | `403` `Please verify your email address to continue.` |
| sessão válida e verificada, papel `user` | `403` `Administrator access is required.` |
| papel `admin` | a rota responde |

O papel lê-se **da base de dados em cada pedido**, não do token. Promover ou despromover uma conta (`make_admin`, ou à mão) vale logo no pedido seguinte, sem a pessoa voltar a entrar.

## `GET /api/admin/me`

Devolve o perfil da conta administradora (`UserRead`: `id`, `name`, `email`, `role`, `is_verified`, ...). O frontend usa-o para decidir se mostra a área de administração: `200` é admin, `403` é utilizador normal, `401` não tem sessão.

## Acrescentar uma rota

Regista-a no `router` de `app/domains/admin/router.py`; a dependência já está lá e não se repete nas rotas. O teste `tests/test_admin_access.py` percorre todas as rotas `/api/admin` do esquema OpenAPI e exige `401` para anónimos e `403` para um utilizador normal, por isso uma rota com o prefixo `/api/admin` que fique sem a verificação falha o CI.
