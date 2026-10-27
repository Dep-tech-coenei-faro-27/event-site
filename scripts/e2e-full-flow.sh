#!/bin/sh
# Teste do fluxo completo (issue #281): arranca o backend a sério (uvicorn) sobre uma
# base de dados descartável, já migrada, e corre `tests/e2e/full_flow.py` contra ele.
# Regista contas e compra bilhetes, por isso SÓ numa base que se deita fora: o script
# Python recusa correr sem E2E_DISPOSABLE_DB igual a POSTGRES_DB, fora de `dev`, sem o
# gateway simulado ou com um servidor de email configurado.
#
# Corre dentro de `backend/`, com o ambiente do servidor já definido (ver
# docs/testes-e2e.md). Variáveis:
#   E2E_PORT        porta do servidor (por omissão 8000)
#   E2E_SERVER_LOG  ficheiro dos registos do servidor (por omissão um temporário)
#   E2E_RUN         comando que corre Python no ambiente (por omissão "uv run")
#
# Sai com o código do teste. Quando falha, mostra os registos do servidor.

PORT="${E2E_PORT:-8000}"
LOG="${E2E_SERVER_LOG:-$(mktemp)}"
RUN="${E2E_RUN:-uv run}"
export E2E_BASE_URL="http://127.0.0.1:$PORT"

# Another server on the port would answer instead of this one.
if curl -fsS "$E2E_BASE_URL/api/health" > /dev/null 2>&1; then
  echo "FAILED  port $PORT is already in use"
  exit 1
fi

$RUN uvicorn app.main:app --port "$PORT" > "$LOG" 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null; wait "$server" 2>/dev/null' EXIT

ready=0
for _ in $(seq 1 30); do
  if curl -fsS "$E2E_BASE_URL/api/health" > /dev/null 2>&1; then ready=1; break; fi
  kill -0 "$server" 2>/dev/null || break
  sleep 1
done

status=1
if [ "$ready" -eq 1 ]; then
  status=0
  $RUN python -m tests.e2e.full_flow || status=$?
else
  echo "FAILED  the server did not start"
fi

if [ "$status" -ne 0 ]; then
  echo "--- server log ---"
  cat "$LOG"
fi
exit "$status"
