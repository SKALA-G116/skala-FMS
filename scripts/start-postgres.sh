#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PG_BIN=${PG_BIN:-/opt/homebrew/opt/postgresql@17/bin}
if [ ! -f .local/pgdata/PG_VERSION ]; then "$PG_BIN/initdb" -D .local/pgdata -A trust --no-locale -E UTF8; fi
if ! "$PG_BIN/pg_ctl" -D .local/pgdata status >/dev/null 2>&1; then "$PG_BIN/pg_ctl" -D .local/pgdata -l .local/postgres.log -o '-p 55432 -h 127.0.0.1 -k /tmp' start; fi
if ! "$PG_BIN/psql" -h 127.0.0.1 -p 55432 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='food_agent'" | rg -q 1; then "$PG_BIN/createdb" -h 127.0.0.1 -p 55432 food_agent; fi
