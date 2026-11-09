#!/bin/sh
# Cópia de segurança da base de dados e dos ficheiros de media.
# Uso, na pasta do projeto: scripts/backup.sh [pasta]   (por omissão, backups/)
# Os ficheiros têm dados pessoais, por isso ficam só legíveis por quem os criou.
set -e

dir="${1:-backups}"
stamp="$(date +%Y%m%d-%H%M%S)"
compose="docker compose --env-file backend/.env"

umask 077
mkdir -p "$dir"

db="$dir/db-$stamp.dump"
if ! $compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$db"; then
    rm -f "$db"
    echo "A cópia da base de dados falhou." >&2
    exit 1
fi
echo "Base de dados: $db"

if [ -d backend/media ]; then
    tar -czf "$dir/media-$stamp.tar.gz" -C backend media
    echo "Media:         $dir/media-$stamp.tar.gz"
else
    echo "Media:         sem pasta backend/media, nada a copiar"
fi
