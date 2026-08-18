#!/bin/sh
set -eu

backup_root=${BACKUP_ROOT:-/backups}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="$backup_root/$stamp"
mkdir -p "$target"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-kechuang}" -d "${POSTGRES_DB:-kechuang}" -Fc > "$target/database.dump"
docker compose run --rm --no-deps -v "$target:/backup" backend sh -c "tar -C /app/media -czf /backup/media.tar.gz ."
cp .env "$target/environment.snapshot"
chmod 600 "$target/environment.snapshot"

find "$backup_root" -mindepth 1 -maxdepth 1 -type d -mtime +"${BACKUP_RETENTION_DAYS:-30}" -exec rm -rf -- {} +
printf '%s\n' "Backup created: $target"
