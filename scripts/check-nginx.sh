#!/bin/sh
# Verifica a configuração do nginx do frontend na mesma imagem do Dockerfile:
#   1. `nginx -t` sem erros nem avisos (p. ex. «conflicting server name»);
#   2. os tokens de /conta/* e a chave do callback de pagamento não ficam no log de acessos,
#      nem no endereço nem no Referer, e um pedido para o callback que falhe não põe a chave
#      no log de erros;
#   3. as páginas /conta/* respondem com Referrer-Policy: no-referrer.
# Precisa de Docker. Uso: sh scripts/check-nginx.sh
set -eu

FRONTEND=$(cd "$(dirname "$0")/../frontend" && pwd)
IMAGE=$(sed -n 's/^FROM \(nginxinc\/[^ ]*\).*/\1/p' "$FRONTEND/Dockerfile")
NAME="check-nginx-$$"
PORT=${CHECK_NGINX_PORT:-18080}
HTML=$(mktemp -d)
echo ok > "$HTML/index.html"
chmod -R a+rX "$HTML"

cleanup() {
    docker rm -f "$NAME" > /dev/null 2>&1 || true
    docker network rm "$NAME" > /dev/null 2>&1 || true
    rm -rf "$HTML"
}
trap cleanup EXIT

MOUNTS="-v $FRONTEND/nginx.conf.template:/etc/nginx/templates/default.conf.template:ro
        -v $FRONTEND/proxy_backend.conf:/etc/nginx/proxy_backend.conf:ro"

echo "== nginx -t ($IMAGE)"
# shellcheck disable=SC2086
output=$(docker run --rm $MOUNTS --entrypoint sh "$IMAGE" \
    -c '/docker-entrypoint.d/20-envsubst-on-templates.sh > /dev/null && nginx -t' 2>&1)
echo "$output"
if echo "$output" | grep -q '\[warn\]\|\[emerg\]'; then
    echo "FALHOU: o nginx -t deu avisos ou erros"
    exit 1
fi

echo "== segredos nos logs"
# Numa rede própria existe o DNS do Docker (127.0.0.11, o resolver da configuração): sem backend,
# "backend" não resolve logo e /api responde 502 na hora, como quando o backend está em baixo.
docker network create "$NAME" > /dev/null
# shellcheck disable=SC2086
docker run -d --name "$NAME" --network "$NAME" -p "127.0.0.1:$PORT:8080" $MOUNTS \
    -v "$HTML:/usr/share/nginx/html:ro" "$IMAGE" > /dev/null
base="http://127.0.0.1:$PORT"
for _ in $(seq 1 30); do
    curl -fs -o /dev/null "$base/" && break
    sleep 0.5
done

curl -s -o /dev/null "$base/conta/verificar?token=SEGREDO-1"
curl -s -o /dev/null "$base/conta/redefinir?token=SEGREDO-2"
curl -s -o /dev/null -X POST -H "Referer: https://eneiconf.pt/conta/verificar?token=SEGREDO-3" \
    "$base/api/auth/verify-email"
curl -s -o /dev/null -H "Referer: https://eneiconf.pt/conta/redefinir?token=SEGREDO-4" "$base/assets/x.js"
curl -s -o /dev/null "$base/api/payment/callback?key=SEGREDO-5&orderId=ENEI-1&amount=50.00"
policy=$(curl -sI "$base/conta/verificar?token=SEGREDO-6" | tr -d '\r' \
    | sed -n 's/^[Rr]eferrer-[Pp]olicy: //p')

access=$(docker logs "$NAME" 2> /dev/null)
errors=$(docker logs "$NAME" 2>&1 > /dev/null)
status=0

if echo "$access" | grep -q SEGREDO; then
    echo "FALHOU: segredo no log de acessos:"
    echo "$access" | grep SEGREDO
    status=1
fi
if echo "$errors" | grep -q 'SEGREDO-5'; then
    echo "FALHOU: a chave do callback está no log de erros:"
    echo "$errors" | grep 'SEGREDO-5'
    status=1
fi
if [ "$policy" != "no-referrer" ]; then
    echo "FALHOU: /conta/verificar responde Referrer-Policy '$policy' (esperado no-referrer)"
    status=1
fi

if [ "$status" -eq 0 ]; then
    echo "OK: nenhum token nem chave nos logs; /conta/* com Referrer-Policy no-referrer"
fi
exit "$status"
