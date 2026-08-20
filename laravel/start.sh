#!/usr/bin/env bash

# Trap Ctrl+C (SIGINT) to cleanly stop all background processes
cleanup() {
  echo ""
  echo "Shutting down all services..."
  kill $(jobs -p) 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "Starting."
echo "."
echo "."

# 1. Start Laravel HTTP Server
php artisan serve &

# 2. Start Laravel Scheduler
php artisan schedule:work &

# 3. Start Frontend Vite Server
npm run dev &

# 4. Start Python FastAPI MCP Server
(
  cd python || exit
  source .venv/bin/activate
  uvicorn main_mcp:app --reload --host 0.0.0.0 --port 6161
) &

# Keep the script running to wait for Ctrl+C
wait