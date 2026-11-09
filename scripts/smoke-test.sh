#!/bin/sh
# Teste de fumo do backend a correr: confirma que arrancou com o esquema e a configuração
# certos e que as rotas principais respondem como devem. SÓ LÊ: nunca regista contas, não
# entra e não compra, para não criar dados nem mandar emails (no servidor o staging e a
# produção são a mesma base de dados, e um registo manda um email verdadeiro).
#
# Variáveis:
#   SMOKE_BASE   endereço do backend (por omissão http://127.0.0.1:8000)
#   SMOKE_CURL   comando do curl (por omissão "curl"). No servidor corre dentro do contentor:
#                SMOKE_CURL="docker compose ... exec -T backend curl"
#
# Sai com 0 se tudo responde como esperado e com 1 se alguma verificação falha.

BASE="${SMOKE_BASE:-http://127.0.0.1:8000}"
CURL="${SMOKE_CURL:-curl}"
failures=0

# check <nome> <código esperado> <método> <caminho> [corpo JSON] [texto que a resposta deve ter]
check() {
  name="$1"; expected="$2"; method="$3"; path="$4"; body="${5:-}"; needle="${6:-}"
  if [ -n "$body" ]; then
    out=$($CURL -sS -m 10 -X "$method" -H 'Content-Type: application/json' -d "$body" \
      -w '\n%{http_code}' "$BASE$path" 2>&1)
  else
    out=$($CURL -sS -m 10 -X "$method" -w '\n%{http_code}' "$BASE$path" 2>&1)
  fi
  code=$(printf '%s\n' "$out" | tail -n 1)
  content=$(printf '%s\n' "$out" | sed '$d')
  if [ "$code" != "$expected" ]; then
    echo "FALHOU  $name: esperava $expected e veio '$code'"
    failures=$((failures + 1))
  elif [ -n "$needle" ] && ! printf '%s' "$content" | grep -q "$needle"; then
    echo "FALHOU  $name: a resposta não tem '$needle'"
    failures=$((failures + 1))
  else
    echo "OK      $name ($code)"
  fi
}

check "saúde" 200 GET /api/health
check "pronto (base de dados)" 200 GET /api/health/ready
check "modalidades (lê a base de dados)" 200 GET /api/payment/tiers "" '"sale_open"'
check "callback sem chave é recusado" 403 GET /api/payment/callback
check "comprar sem sessão é recusado" 401 POST /api/payment/initiate \
  '{"ticket_tier":"geral","phone":"912345678"}'
check "perfil sem sessão é recusado" 401 GET /api/users/me

# As quatro modalidades têm de existir (a migration cria-as).
tiers=$($CURL -sS -m 10 "$BASE/api/payment/tiers" 2>/dev/null | grep -o '"tier":"' | wc -l)
if [ "${tiers:-0}" -lt 4 ]; then
  echo "FALHOU  modalidades: esperava pelo menos 4 e vieram ${tiers:-0}"
  failures=$((failures + 1))
else
  echo "OK      modalidades: $tiers"
fi

if [ "$failures" -ne 0 ]; then
  echo "Teste de fumo: $failures verificação(ões) falharam."
  exit 1
fi
echo "Teste de fumo: tudo OK."
