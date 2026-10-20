#!/bin/sh
# Escreve métricas para o node-exporter. Corre todos os minutos no cron.
set -u
PROJECT_DIR="${PROJECT_DIR:-/home/debian/enei/event-site}"
METRICS_DIR="${METRICS_DIR:-/home/debian/enei/metrics}"
BACKUP_DIR="${BACKUP_DIR:-/home/debian/enei/backups}"
cd "$PROJECT_DIR" || exit 1
[ -d "$METRICS_DIR" ] || { echo "Falta $METRICS_DIR" >&2; exit 1; }

status="$(docker compose --env-file backend/.env --env-file tunnel.env exec -T backend \
  /app/.venv/bin/python -m app.core.email --status 2>/dev/null)" || status=""
num() { printf '%s\n' "$status" | grep -oE "$1[\"'= :]*[0-9.]+" | head -n1 | grep -oE '[0-9.]+$'; }
oldest="$(num oldest_pending_seconds)"
failed="$(num failed)"

tmp="$(mktemp "$METRICS_DIR/.enei.XXXXXX")"
{
  if [ -n "$failed" ]; then
    echo "enei_email_status_ok 1"
    echo "enei_email_oldest_pending_seconds ${oldest:-0}"
    echo "enei_email_failed $failed"
  else
    echo "enei_email_status_ok 0"
  fi
  if [ -f "$BACKUP_DIR/offsite-last-success" ]; then
    echo "enei_backup_last_success_timestamp_seconds $(stat -c %Y "$BACKUP_DIR/offsite-last-success")"
  fi
} > "$tmp"
chmod 644 "$tmp"
mv "$tmp" "$METRICS_DIR/enei.prom"