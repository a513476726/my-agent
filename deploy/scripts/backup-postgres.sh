#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/deploy/compose/docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/data/backups}"
POSTGRES_USER="${POSTGRES_USER:-myagent}"
POSTGRES_DB="${POSTGRES_DB:-myagent}"

# 仅用于 Compose 变量插值；pg_dump 在容器内通过本地连接执行，不依赖该值。
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-compose-interpolation-only}"
export AUTH_SECRET="${AUTH_SECRET:-compose-interpolation-only}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-compose-interpolation-only}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
output="$BACKUP_DIR/myagent-$timestamp.dump"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$output"

printf 'backup written: %s\n' "$output"
