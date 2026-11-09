#!/bin/sh
# Cópia de segurança para fora da VPS: dump da base de dados e media, copiados com o rclone.
#
# Variáveis:
#   BACKUP_REMOTE            obrigatória. Destino do rclone, formato nome-do-remote:pasta.
#                            O remote tem de ser do tipo "crypt" (cifrado): o dump tem dados pessoais.
#   BACKUP_ALLOW_PLAINTEXT   1 para aceitar um destino sem cifra (só para testes; nunca em produção).
#   BACKUP_HEARTBEAT_URL     opcional. Endereço de um serviço de monitorização com a convenção do
#                            Healthchecks (URL, URL/start e URL/fail). Se a cópia falhar ou não correr,
#                            o serviço avisa. O endereço é tratado como segredo.
#   BACKUP_STATUS_FILE       ficheiro onde se regista o instante da última cópia bem-sucedida
#                            (por omissão, $BACKUP_DIR/offsite-last-success). Ver scripts/check-offsite-backup.sh.
#   PROJECT_DIR, BACKUP_DIR  pastas do projeto e das cópias na VPS.
set -eu
umask 077

PROJECT_DIR="${PROJECT_DIR:-/home/debian/enei/event-site}"
BACKUP_DIR="${BACKUP_DIR:-/home/debian/enei/backups}"
REMOTE="${BACKUP_REMOTE:?Define BACKUP_REMOTE antes de executar}"
REMOTE_NAME="${REMOTE%%:*}"
STATUS_FILE="${BACKUP_STATUS_FILE:-$BACKUP_DIR/offsite-last-success}"
HEARTBEAT_URL="${BACKUP_HEARTBEAT_URL:-}"

ping_heartbeat() {
    [ -n "$HEARTBEAT_URL" ] || return 0
    curl -fsS -m 10 --retry 3 -o /dev/null "$HEARTBEAT_URL$1" ||
        echo "Aviso: não consegui contactar o serviço de monitorização." >&2
}

# Qualquer falha (set -e, rclone, backup.sh) avisa o serviço de monitorização.
on_exit() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "A cópia externa falhou (código $status)." >&2
        ping_heartbeat /fail
    fi
}
trap on_exit EXIT

# Recusa um destino sem cifra: as cópias levam emails, nomes e (com pagamentos) telemóveis.
if [ "${BACKUP_ALLOW_PLAINTEXT:-0}" != "1" ]; then
    remote_type="$(rclone listremotes --long | awk -v n="$REMOTE_NAME:" '$1 == n { print $2 }')"
    if [ "$remote_type" != "crypt" ]; then
        echo "ERRO: o destino '$REMOTE_NAME' não é um remote do tipo crypt (é '${remote_type:-desconhecido}')." >&2
        echo "Cria um remote crypt por cima do destino (rclone config) e usa-o em BACKUP_REMOTE." >&2
        exit 1
    fi
fi

ping_heartbeat /start

cd "$PROJECT_DIR"

/bin/sh scripts/backup.sh "$BACKUP_DIR"

rclone copy "$BACKUP_DIR" "$REMOTE" \
    --include 'db-*.dump' \
    --include 'media-*.tar.gz'

# Retenção em destino: 30 dias. Quem pede o apagamento da conta continua nestas cópias até
# expirarem; a política de privacidade tem de o dizer.
rclone delete "$REMOTE" --min-age 30d \
    --include 'db-*.dump' \
    --include 'media-*.tar.gz'

find "$BACKUP_DIR" -type f \
    \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) \
    -mmin +10080 -delete

date +%s > "$STATUS_FILE"
ping_heartbeat ""

echo "Backup e cópia remota concluídos."
