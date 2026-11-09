#!/bin/sh
# Sai com código 1 se a última cópia externa bem-sucedida tem mais de N horas (26 por omissão)
# ou se nunca houve nenhuma. Serve para a verificação final e para ligar a um alerta.
# Uso: scripts/check-offsite-backup.sh [horas]
set -eu

BACKUP_DIR="${BACKUP_DIR:-/home/debian/enei/backups}"
STATUS_FILE="${BACKUP_STATUS_FILE:-$BACKUP_DIR/offsite-last-success}"
MAX_HOURS="${1:-26}"

if [ ! -f "$STATUS_FILE" ]; then
    echo "Nenhuma cópia externa registada em $STATUS_FILE." >&2
    exit 1
fi

last="$(cat "$STATUS_FILE")"
now="$(date +%s)"
age_hours=$(((now - last) / 3600))

if [ "$age_hours" -gt "$MAX_HOURS" ]; then
    echo "A última cópia externa tem $age_hours h (o limite é $MAX_HOURS h)." >&2
    exit 1
fi

echo "A última cópia externa tem $age_hours h."
