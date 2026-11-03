#!/usr/bin/env bash
# Install or replace only the marked 3BPay daily-backup cron entries.
set -euo pipefail

ROOT="${THREEBPAY_ROOT:-/opt/3bpay}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
MARKER='# 3bpay-daily-backup'
mkdir -p "$BACKUP_DIR"
touch "$BACKUP_DIR/backup.log"
chmod 600 "$BACKUP_DIR/backup.log"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
(crontab -l 2>/dev/null || true) | grep -vF "$MARKER" | grep -vF 'CRON_TZ=America/New_York' > "$tmp" || true
{
  echo 'CRON_TZ=America/New_York'
  echo "0 3 * * * umask 077; /usr/bin/flock -n $BACKUP_DIR/.backup.cron.lock /bin/bash $ROOT/deploy/backup.sh >> $BACKUP_DIR/backup.log 2>&1 $MARKER"
} >> "$tmp"
crontab "$tmp"
echo 'Installed 3BPay daily backup at 03:00 America/New_York.'
