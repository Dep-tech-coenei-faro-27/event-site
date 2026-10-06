#!/bin/sh
# Restaura uma cópia da base de dados para uma base NOVA, que não pode existir.
# Para testar uma cópia, use um nome como event_site_restore.
# Para repor a base verdadeira: pare o backend, apague a base e restaure com o mesmo nome.
# Uso, na pasta do projeto: scripts/restore.sh ficheiro.dump nome_da_base
set -e

if [ "$#" -ne 2 ]; then
    echo "Uso: scripts/restore.sh ficheiro.dump nome_da_base" >&2
    exit 1
fi

dump="$1"
target="$2"
compose="docker compose --env-file backend/.env"

if [ ! -f "$dump" ]; then
    echo "Ficheiro não encontrado: $dump" >&2
    exit 1
fi

$compose exec -T postgres sh -c "createdb -U \"\$POSTGRES_USER\" \"$target\""
$compose exec -T postgres sh -c "pg_restore -U \"\$POSTGRES_USER\" --no-owner -d \"$target\"" < "$dump"

echo "Restaurado em $target"
