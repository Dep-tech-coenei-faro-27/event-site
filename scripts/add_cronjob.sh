
#!/bin/sh
# Agenda export-metrics.sh de minuto a minuto, se ainda não estiver agendado.
set -eu

PROJECT_DIR="/home/debian/enei/event-site"
DATA_DIR="/home/debian/enei"

CRON_LINE="* * * * * cd $PROJECT_DIR && flock -n /tmp/enei-metrics.lock /bin/sh scripts/export-metrics.sh >> $DATA_DIR/export-metrics.log 2>&1"

CURRENT_CRON="$(crontab -l 2>/dev/null || true)"

if printf '%s\n' "$CURRENT_CRON" | grep -Fq 'scripts/export-metrics.sh'; then
    echo "Cron do export-metrics.sh já agendado. Nada a fazer."
    exit 0
fi

mkdir -p "$DATA_DIR"

{
    printf '%s\n' "$CURRENT_CRON"
    printf '%s\n' "$CRON_LINE"
} | crontab -

echo "Cron do export-metrics.sh agendado com sucesso."
