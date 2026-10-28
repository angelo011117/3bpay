#!/usr/bin/env bash
set -euo pipefail

ROOT="${THREEBPAY_ROOT:-/opt/3bpay}"
ENV_FILE="${THREEBPAY_ENV_FILE:-$ROOT/.env.production}"
COMPOSE_FILE="$ROOT/docker-compose.production.yml"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

test -f "$ENV_FILE"
test -f "$COMPOSE_FILE"
case "$BACKUP_DIR" in /|"") echo 'Refusing unsafe BACKUP_DIR' >&2; exit 2;; esac
set -a; . "$ENV_FILE"; set +a
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$BACKUP_DIR/$stamp"
mkdir -p "$target"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$target/database.dump"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  tar -C /app/media -czf - . > "$target/media.tar.gz"
sha256sum "$target/database.dump" "$target/media.tar.gz" > "$target/SHA256SUMS"
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -print -exec rm -rf -- {} +
echo "Backup created: $target"
