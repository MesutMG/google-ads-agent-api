   #=====================================
#========== Deletes The Project ============
   #=====================================

set -e

CONTAINER_NAME="ads-analyzer-backend"
IMAGE_NAME="google-ads-analyzer-python"

echo "==> Stopping and removing containers..."
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    docker compose down --volumes --remove-orphans 2>/dev/null || true
fi

# Fallback: force remove container by name if it still exists
if [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
    docker rm -f "$CONTAINER_NAME"
    echo "Removed container: $CONTAINER_NAME"
fi

echo "==> Removing image..."
if [ "$(docker images -q "$IMAGE_NAME" 2> /dev/null)" ]; then
    docker rmi -f "$IMAGE_NAME"
    echo "Removed image: $IMAGE_NAME"
fi

echo "==> Pruning dangling Docker build cache and unused volumes..."
docker builder prune -f
docker volume prune -f

echo "==> Docker cleanup complete."