#!/bin/sh
# Constrói a imagem do backend (backend/Dockerfile) e arranca-a como no servidor: o
# entrypoint aplica as migrations e o uvicorn arranca com ENVIRONMENT=prod, por isso a
# validação da configuração de produção também corre. Espera até 30 s por /api/health,
# corre o teste de fumo (só lê) e falha, mostrando os registos do contentor, se o
# contentor parar ou não responder a tempo.
#
# Precisa de Docker e de uma base PostgreSQL só para isto (as migrations correm nela).
# Não sai nenhum email: SMTP_HOST aponta para um domínio que não existe (.invalid) e o
# worker do outbox está desligado. O contentor usa a rede do anfitrião e a porta 8000.
#
# Variáveis: POSTGRES_HOST (127.0.0.1), POSTGRES_PORT (5432), POSTGRES_USER (postgres),
# POSTGRES_PASSWORD e POSTGRES_DB (obrigatórias). A palavra-passe não pode ser "postgres":
# a validação de produção recusa-a.
#
# Uso: POSTGRES_PORT=5434 POSTGRES_PASSWORD=... POSTGRES_DB=tmp sh scripts/check-backend-container.sh
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${CHECK_CONTAINER_IMAGE:-event-site-backend:check}
NAME="check-backend-$$"
ENV_FILE=$(mktemp)
: "${POSTGRES_PASSWORD:?Defina POSTGRES_PASSWORD}"
: "${POSTGRES_DB:?Defina POSTGRES_DB}"

cleanup() {
    docker rm -f "$NAME" > /dev/null 2>&1 || true
    rm -f "$ENV_FILE"
}
trap cleanup EXIT

secret() {
    head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
}

cat > "$ENV_FILE" <<EOF
ENVIRONMENT=prod
DEBUG=false
POSTGRES_HOST=${POSTGRES_HOST:-127.0.0.1}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
JWT_SECRET_KEY=$(secret)
QR_SECRET_KEY=$(secret)
SMTP_HOST=smtp.invalid
EMAIL_SENDER=noreply@example.com
EMAIL_OUTBOX_WORKER=0
FRONTEND_URL=https://example.com
CORS_ALLOW_ORIGINS=["https://example.com"]
EOF

echo "== docker build ($IMAGE)"
docker build -q -t "$IMAGE" "$ROOT/backend"

echo "== docker run"
docker run -d --name "$NAME" --network host --env-file "$ENV_FILE" "$IMAGE" > /dev/null

ok=""
for i in $(seq 1 30); do
    if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" != "true" ]; then
        echo "FALHOU: o contentor parou (código $(docker inspect -f '{{.State.ExitCode}}' "$NAME"))"
        break
    fi
    if curl -fsS -m 2 http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        ok=1
        echo "/api/health respondeu ao fim de ${i} s"
        break
    fi
    sleep 1
done

status=0
if [ -z "$ok" ]; then
    [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = "true" ] \
        && echo "FALHOU: /api/health não respondeu em 30 s"
    status=1
else
    sh "$ROOT/scripts/smoke-test.sh" || status=$?
fi

if [ "$status" -ne 0 ]; then
    echo "== registos do contentor"
    docker logs "$NAME" 2>&1 | tail -n 100
fi
exit "$status"
