   #=====================================
#========== Deletes The Project ============
   #=====================================

#!/usr/bin/env bash
set -e

echo "==> Stopping service and wiping all related containers, networks, and images..."
docker compose down --volumes --rmi all --remove-orphans 2>/dev/null || true

docker rm -f google-ads-agent-api 2>/dev/null || true
docker rmi -f google-ads-agent-api 2>/dev/null || true

echo "==> Pruning build caches..."
docker builder prune -f

echo "==> Cleanup complete. Everything related to google-ads-agent-api has been removed."