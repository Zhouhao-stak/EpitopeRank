#!/usr/bin/env bash
# Incremental source update for the EpitopeRank container on this host.
#
#   ./deploy/server/update-container.sh [bundle.tar.gz]
#
# Without an argument the newest .upload/epitoperank-server-*.tar.gz is used.
# The image is never rebuilt: the source tree is bind-mounted over /app by
# docker-compose.server.yml, so a file update plus a container recreate is all
# that is needed. Every run keeps a rollback copy under .backup-<timestamp>/.
set -euo pipefail

ROOT="${EPITOPERANK_ROOT:-$HOME/epitoperank}"
cd "$ROOT"

BUNDLE="${1:-}"
if [ -z "$BUNDLE" ]; then
  BUNDLE="$(ls -1t .upload/epitoperank-server-*.tar.gz 2>/dev/null | head -n 1 || true)"
fi
if [ -z "$BUNDLE" ] || [ ! -f "$BUNDLE" ]; then
  echo "bundle not found; pass a .tar.gz path or put one in .upload/" >&2
  exit 1
fi

TS="$(date +%Y%m%d-%H%M%S)"
BACKUP=".backup-$TS"
mkdir -p "$BACKUP" .upload

echo "[1/7] backup source + compose files -> $BACKUP"
tar -czf "$BACKUP/source.tar.gz" \
  epitoperank run.py serve_ui.py deploy docs examples scripts tests 2>/dev/null || true
cp -a docker-compose.yml docker-compose.override.yml .env "$BACKUP/" 2>/dev/null || true
[ -f docker-compose.server.yml ] && cp -a docker-compose.server.yml "$BACKUP/" || true

echo "[2/7] extract $BUNDLE"
tar -xzf "$BUNDLE" -C "$ROOT"

echo "[3/7] clean stale bytecode (Windows/old Python caches)"
find epitoperank -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find epitoperank -name '*.pyc' -delete 2>/dev/null || true

# COMPOSE_FILE points at the project root, so the server override must exist
# there (the tracked copy lives under deploy/server/).
cp -f deploy/server/docker-compose.server.yml docker-compose.server.yml

chmod +x deploy/docker/entrypoint.sh deploy/server/*.sh 2>/dev/null || true

echo "[4/7] ensure COMPOSE_FILE in .env"
COMPOSE_LIST="docker-compose.yml:docker-compose.override.yml:docker-compose.server.yml"
if grep -q '^COMPOSE_FILE=' .env 2>/dev/null; then
  sed -i "s|^COMPOSE_FILE=.*|COMPOSE_FILE=$COMPOSE_LIST|" .env
else
  printf '\n# Added by deploy/server/update-container.sh: bind-mount source for incremental updates\nCOMPOSE_FILE=%s\n' "$COMPOSE_LIST" >> .env
fi
export COMPOSE_FILE="$COMPOSE_LIST"

echo "[5/7] compose config check"
docker compose config -q

echo "[6/7] preflight import with the new source (no container restart yet)"
timeout 180 docker compose run --rm --no-deps --entrypoint python epitoperank \
  -c "import epitoperank.api.app, epitoperank.peptide, epitoperank.agent.copilot; print('import-ok')"

echo "[7/7] recreate container from the existing image"
# The source is bind-mounted, so a code-only change does not alter the compose
# config and plain `up -d` would leave the old processes running. Force a
# recreate so every worker imports the new files.
docker compose up -d --force-recreate --no-build

echo "waiting for health..."
for _ in $(seq 1 80); do
  if curl -fsS -m 5 http://127.0.0.1:8800/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

echo "--- health ---"
curl -fsS http://127.0.0.1:8800/api/health; echo
echo "--- copilot tools ---"
curl -fsS http://127.0.0.1:8800/api/copilot/tools | head -c 240; echo
echo "--- peptide capabilities ---"
curl -fsS http://127.0.0.1:8800/api/peptide/capabilities | head -c 240; echo
echo "--- container ---"
docker compose ps
echo "rollback: ./deploy/server/rollback-container.sh $BACKUP"
