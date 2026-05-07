#!/usr/bin/env bash
# Start Ultron v3 — backend (FastAPI) + frontend (Vite dev) in parallel
set -e

cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true

echo "==> Starting backend on http://localhost:8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

if [ -d frontend/node_modules ]; then
    echo "==> Starting frontend dev server on http://localhost:5173"
    (cd frontend && npm run dev) &
    FRONTEND_PID=$!
    URL="http://localhost:5173"
else
    echo "==> Frontend node_modules missing — run 'cd frontend && npm install' first"
    URL="http://localhost:8000  (API only)"
fi

cleanup() {
    echo
    echo "Stopping..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo
echo "✅ Ultron is running."
echo "   Open: $URL"
echo "   Press Ctrl+C to stop."
echo
wait
