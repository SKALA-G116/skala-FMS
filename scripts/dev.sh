#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
./scripts/start-postgres.sh
if [ -f .env.food ]; then set -a; . ./.env.food; set +a; fi
.venv/bin/python -m backend.app.domains.jobs.worker &
worker_pid=$!
trap 'kill "$worker_pid" 2>/dev/null || true' EXIT INT TERM
.venv/bin/uvicorn backend.app.api.main:app --host 127.0.0.1 --port 8100
