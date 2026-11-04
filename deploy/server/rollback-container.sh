#!/usr/bin/env bash
# Restore the source tree and compose files from a backup made by
# update-container.sh, then recreate the container from the same image.
#
#   ./deploy/server/rollback-container.sh [.backup-YYYYmmdd-HHMMSS]
set -euo pipefail

ROOT="${SPLICEGAIP_ROOT:-$HOME/splicegaip}"
cd "$ROOT"

BACKUP="${1:-$(ls -1dt .backup-* 2>/dev/null | head -n 1 || true)}"
if [ -z "$BACKUP" ] || [ ! -f "$BACKUP/source.tar.gz" ]; then
  echo "no usable backup found (expected $BACKUP/source.tar.gz)" >&2
  exit 1
fi

echo "[1/3] restore source from $BACKUP/source.tar.gz"
tar -xzf "$BACKUP/source.tar.gz" -C "$ROOT"
if [ -f "$BACKUP/docker-compose.server.yml" ]; then
  cp -a "$BACKUP/docker-compose.server.yml" "$ROOT/docker-compose.server.yml"
fi
if [ -f "$BACKUP/.env" ]; then
  cp -a "$BACKUP/.env" "$ROOT/.env"
fi

export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml:docker-compose.override.yml:docker-compose.server.yml}"
echo "[2/3] compose config check"
docker compose config -q

echo "[3/3] recreate container"
docker compose up -d --no-build
for _ in $(seq 1 60); do
  if curl -fsS -m 5 http://127.0.0.1:8800/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
curl -fsS http://127.0.0.1:8800/api/health; echo
docker compose ps
