#!/usr/bin/env bash
# Validates a backup in a new disposable PostgreSQL container and volume only.
set -euo pipefail

backup_dir="${1:?Usage: verify-restore-isolated.sh /path/to/backup}"
test -f "$backup_dir/database.dump"
test -f "$backup_dir/SHA256SUMS"
(cd "$backup_dir" && sha256sum -c SHA256SUMS)
name="3bpay_restore_check_$(date +%s)"
volume="${name}_data"
password="restore-check-only"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; docker volume rm "$volume" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker volume create "$volume" >/dev/null
docker run -d --name "$name" --network none -e POSTGRES_PASSWORD="$password" -e POSTGRES_USER=restore -e POSTGRES_DB=restore -v "$volume:/var/lib/postgresql/data" postgres:16-alpine >/dev/null
until docker exec "$name" pg_isready -U restore -d restore >/dev/null 2>&1; do sleep 1; done
docker exec -i "$name" pg_restore -U restore -d restore --clean --if-exists --no-owner --no-privileges < "$backup_dir/database.dump"
docker exec "$name" psql -U restore -d restore -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
echo 'Isolated database restore verified; disposable container and volume will be removed.'
