#!/usr/bin/env bash
set -euo pipefail

if [[ "${ALLOW_RESTORE:-0}" != "1" ]]; then
  echo "恢复会覆盖当前数据库；确认后设置 ALLOW_RESTORE=1 再执行。" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/deploy/compose/docker-compose.yml}"
POSTGRES_USER="${POSTGRES_USER:-myagent}"
POSTGRES_DB="${POSTGRES_DB:-myagent}"

# 仅用于 Compose 变量插值；pg_restore 在容器内通过本地连接执行。
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-compose-interpolation-only}"
export AUTH_SECRET="${AUTH_SECRET:-compose-interpolation-only}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-compose-interpolation-only}"

if [[ $# -ne 1 ]]; then
  echo "用法: ALLOW_RESTORE=1 $0 <backup.dump>" >&2
  exit 2
fi
backup="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
if [[ ! -f "$backup" ]]; then
  echo "备份文件不存在: $backup" >&2
  exit 2
fi

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner < "$backup"

printf 'restore completed: %s\n' "$backup"
