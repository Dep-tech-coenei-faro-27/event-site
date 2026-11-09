# Contraste texto/fundo do frontend

Razões de contraste (WCAG 2.x) entre as cores de texto e as superfícies do site. O mínimo é **4,5:1** (AA, texto normal).
As cores vêm do `frontend/tailwind.config.js`; as variáveis CSS das páginas usam as mesmas (`--bg` = azul-base, `--panel` = azul-painel,
`--surface` = azul-superficie, `--panel-strong` = azul-elevado, `--text` = branco, `--muted` = cinza-texto, `--subtle` = cinza-subtil).

O teste `frontend/src/contrast.test.tsx` lê a paleta do mesmo ficheiro e falha se algum destes pares descer abaixo de 4,5:1.

## Texto claro sobre as superfícies escuras

| Texto \ Fundo | azul-noite `#030710` | azul-base `#050D21` | azul-superficie `#081126` | azul-painel `#0A172F` | azul-faq `#0A1930` | azul-elevado `#0D1A34` |
|---|---:|---:|---:|---:|---:|---:|
| branco `#FFFFFF` | 20,16 | 19,34 | 18,78 | 17,85 | 17,58 | 17,29 |
| gelo `#D7E3F4` | 15,53 | 14,90 | 14,47 | 13,76 | 13,55 | 13,33 |
| cinza-texto `#B1BCCD` | 10,51 | 10,08 | 9,78 | 9,30 | 9,16 | 9,01 |
| nevoa-azul `#AAB7C9` | 9,91 | 9,51 | 9,23 | 8,78 | 8,64 | 8,50 |
| cinza-subtil `#8796A9` | 6,69 | 6,41 | 6,23 | 5,92 | 5,83 | 5,74 |
| acento-principal `#1AB2FF` | 8,50 | 8,15 | 7,92 | 7,53 | 7,41 | 7,29 |
| acento-forte `#23CAFF` | 10,52 | 10,10 | 9,80 | 9,32 | 9,18 | 9,03 |
| ciano-digital `#00AAFF` | 7,87 | 7,55 | 7,33 | 6,96 | 6,86 | 6,75 |
| verde-agua `#5BD6C4` | 11,39 | 10,92 | 10,60 | 10,08 | 9,93 | 9,77 |
| pervinca `#AAB4FF` | 10,25 | 9,84 | 9,55 | 9,08 | 8,94 | 8,80 |
| indigo-beneficio `#8F9CFF` | 8,03 | 7,70 | 7,48 | 7,11 | 7,00 | 6,89 |
| ouro `#F4C542` | 12,39 | 11,89 | 11,54 | 10,97 | 10,81 | 10,63 |
| coral-vivo `#FF8F84` | 9,13 | 8,76 | 8,51 | 8,09 | 7,96 | 7,83 |

## Texto escuro sobre ciano (botões, etiquetas, «Saltar para o conteúdo»)

| Texto | Fundo | Razão |
|---|---|---:|
| texto-de-acao `#03101D` | acento-principal `#1AB2FF` | 8,08 |
| texto-sobre-ciano `#02101C` | acento-forte `#23CAFF` | 10,03 |
| azul-base `#050D21` | acento-principal `#1AB2FF` | 8,15 |

## Corrigido

| Onde | Antes | Depois |
|---|---|---:|
| «A carregar…» do `ProtectedRoute` (fundo azul-base) | preto `#000000`: 1,09 | nevoa-azul: 9,51 |
