#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  printf '%s\n' "Usage: $0 /backups/YYYYMMDDTHHMMSSZ" >&2
  exit 2
fi

source_dir=$1
test -f "$source_dir/database.dump"
test -f "$source_dir/media.tar.gz"

docker compose exec -T postgres pg_restore --clean --if-exists --no-owner -U "${POSTGRES_USER:-kechuang}" -d "${POSTGRES_DB:-kechuang}" < "$source_dir/database.dump"
docker compose run --rm --no-deps -v "$source_dir:/backup:ro" backend sh -c "find /app/media -mindepth 1 -delete && tar -C /app/media -xzf /backup/media.tar.gz"
docker compose restart backend celery
printf '%s\n' "Restore completed from: $source_dir"
