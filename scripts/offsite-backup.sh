
#!/bin/sh
set -eu
umask 077

PROJECT_DIR="/home/debian/enei/event-site"
BACKUP_DIR="$PROJECT_DIR/backups"
REMOTE="${BACKUP_REMOTE:?Define BACKUP_REMOTE antes de executar}"

cd "$PROJECT_DIR"

/bin/sh scripts/backup.sh "$BACKUP_DIR"

rclone copy "$BACKUP_DIR" "$REMOTE" \
    --include 'db-*.dump' \
    --include 'media-*.tar.gz'


rclone delete "$REMOTE" --min-age 30d

find "$BACKUP_DIR" -type f \
    \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) \
    -mmin +10080 -delete

echo "Backup e cópia remota concluídos."
