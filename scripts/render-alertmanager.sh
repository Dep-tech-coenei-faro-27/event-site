#!/bin/sh
# Gera o alertmanager.yml a partir do .tpl. Só leva valores que não são segredos:
# a password do SMTP e o webhook entram por ficheiros montados (ver docker-compose.yml).
# Uso: ALERT_EMAIL_TO=eu@exemplo.pt sh scripts/render-alertmanager.sh backend/.env monitoring/alertmanager.yml
set -eu
umask 022
env_file="$1"; out="$2"
: "${ALERT_EMAIL_TO:?Define ALERT_EMAIL_TO}"
ALERT_SMTP_PORT="${ALERT_SMTP_PORT:-587}"
ALERT_SMTP_REQUIRE_TLS="${ALERT_SMTP_REQUIRE_TLS:-true}"
export ALERT_SMTP_PORT ALERT_SMTP_REQUIRE_TLS
tmp="$out.tmp"; tmpenv="$(mktemp)"
trap 'rm -f "$tmp" "$tmpenv"' EXIT

# O Docker cria uma PASTA onde falta um ficheiro montado: se for o caso, apaga-a (só se estiver vazia).
if [ -d "$out" ]; then rmdir "$out"; fi

grep -E '^(SMTP_HOST|EMAIL_SENDER|SMTP_USER)=' "$env_file" > "$tmpenv" || true
for v in SMTP_HOST EMAIL_SENDER; do
  grep -qE "^$v=.+" "$tmpenv" || { echo "$v está vazio em $env_file." >&2; exit 1; }
done

vars='${SMTP_HOST} ${EMAIL_SENDER} ${SMTP_USER} ${ALERT_EMAIL_TO} ${ALERT_SMTP_PORT} ${ALERT_SMTP_REQUIRE_TLS}'
docker run --rm -i --env-file "$tmpenv" -e ALERT_EMAIL_TO -e ALERT_SMTP_PORT -e ALERT_SMTP_REQUIRE_TLS nginx:1.27-alpine envsubst "$vars" \
  < monitoring/alertmanager.yml.tpl > "$tmp"

# Se sobrou algum ${...}, o .tpl e este script estão dessincronizados (o amtool não o apanharia).
if grep -q '\${' "$tmp"; then
  echo "O alertmanager.yml gerado ainda tem placeholders por substituir:" >&2
  grep -n '\${' "$tmp" >&2
  exit 1
fi
cat "$tmp" > "$out"