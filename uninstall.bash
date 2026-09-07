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

echo "==> Removing generated local files (config.json, logs, caches)..."
rm -f mcp_debug.log
rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__

echo "==> Cleanup complete. Docker artifacts, qwen2.5:3b model, and generated files removed."