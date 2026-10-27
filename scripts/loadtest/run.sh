#!/bin/sh
# Corre um cenário de carga contra o servidor real, nesta máquina, sobre uma base PostgreSQL
# nova criada pelas migrations. No fim pára o servidor e apaga a base.
#
#   scripts/loadtest/run.sh <cenário> [opções do loadtest.py]
#   LATENCY=9 scripts/loadtest/run.sh payments --label "latência 9 s"
#
# O servidor arranca como em produção (o CMD do Dockerfile: um só processo do uvicorn) e com
# os limites, o pool e os tempos por omissão do código (os de produção), mesmo que o
# backend/.env local tenha outros. Para medir outro valor, exporta-o antes, por exemplo
# RATE_LIMIT_LOGIN_PER_IP_PER_MINUTE=120. Nunca manda emails nem cobra: SMTP vazio
# (os emails só vão para o log) e PAYMENTS_MODE=simulated.
#
# Variáveis:
#   LATENCY        segundos que o fornecedor simulado demora a responder (por omissão 1)
#   CONFIRM_AFTER  segundos até o fornecedor simulado dar o pagamento como pago (5)
#   USERS          contas criadas na base (por omissão 2 × --users, para a mistura)
#   PORT           porta do servidor de carga (8100)
#   OUT_DIR        onde ficam os resultados e o log (scripts/loadtest/results)
#
# Lê a ligação ao PostgreSQL (POSTGRES_USER, _PASSWORD, _HOST, _PORT) do backend/.env.
set -eu

[ $# -ge 1 ] || { sed -n '2,20p' "$0"; exit 2; }
scenario="$1"; shift

here=$(cd "$(dirname "$0")" && pwd)
backend="$here/../../backend"
py="$backend/.venv/bin/python"
port="${PORT:-8100}"
out_dir="${OUT_DIR:-$here/results}"
stamp=$(date +%Y%m%d-%H%M%S)
db="loadtest_${scenario}_$(date +%s)"
mkdir -p "$out_dir"
log="$out_dir/$scenario-$stamp.log"

cd "$backend"

# Os valores por omissão do código (os de produção) por cima do backend/.env local.
eval "$("$py" - <<'EOF'
from app.core.config import Settings

PREFIXES = ("RATE_LIMIT_", "DB_POOL_", "DB_MAX_", "EMAIL_OUTBOX_", "PAYMENT_EVENTS_",
            "MBWAY_TIMEOUT_", "MBWAY_PAYMENT_TIMEOUT_", "PAYMENT_PROVIDER_MIN_")
for name, field in Settings.model_fields.items():
    if name.startswith(PREFIXES):
        print(f'export {name}="${{{name}:-{field.default}}}"')
EOF
)"

pg() {
  "$py" - "$@" <<'EOF'
import sys

import psycopg2

from app.core.config import settings

conn = psycopg2.connect(
    dbname="postgres", user=settings.POSTGRES_USER, password=settings.POSTGRES_PASSWORD,
    host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
)
conn.autocommit = True
conn.cursor().execute(sys.argv[1])
EOF
}

db_url=$("$py" -c "
from app.core.config import settings as s
print(f'postgresql://{s.POSTGRES_USER}:{s.POSTGRES_PASSWORD}@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/$db')")

server=""
cleanup() {
  if [ -n "$server" ]; then
    kill "$server" 2>/dev/null || true
    wait "$server" 2>/dev/null || true
  fi
  pg "DROP DATABASE IF EXISTS $db WITH (FORCE)" || true
}
trap cleanup EXIT INT TERM

pg "CREATE DATABASE $db"
export POSTGRES_DB="$db" ENVIRONMENT=dev DEBUG=false RATE_LIMIT_ENABLED=true \
  SMTP_HOST="" SMTP2_HOST="" PAYMENTS_MODE=simulated \
  PAYMENTS_SIMULATED_LATENCY_SECONDS="${LATENCY:-1}" \
  PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS="${CONFIRM_AFTER:-5}"

.venv/bin/alembic upgrade head >/dev/null 2>&1
users="${USERS:-600}"
"$py" "$here/seed.py" --users "$users"

# O mesmo comando do Dockerfile: um só processo (o SSE e a reconciliação estão em memória).
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$port" >"$log" 2>&1 &
server=$!
for _ in $(seq 1 60); do
  curl -fsS -o /dev/null "http://127.0.0.1:$port/api/health/ready" 2>/dev/null && break
  sleep 0.5
done

status=0
"$py" "$here/loadtest.py" "$scenario" --base "http://127.0.0.1:$port" \
  --db-url "$db_url" --pool-limit $((DB_POOL_SIZE + DB_MAX_OVERFLOW)) \
  --server-log "$log" --out "$out_dir/$scenario-$stamp.json" "$@" || status=$?

echo "Resultados: $out_dir/$scenario-$stamp.json (log: $log)"
exit "$status"
