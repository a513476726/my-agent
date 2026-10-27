#!/bin/sh
set -eu

: "${REDIS_PASSWORD:?REDIS_PASSWORD must be set}"

KVROCKS_DIR="${KVROCKS_DIR:-/var/lib/kvrocks}"
mkdir -p "$KVROCKS_DIR"

{
  echo "bind 0.0.0.0"
  echo "port 6379"
  echo "dir $KVROCKS_DIR"
  printf 'requirepass %s\n' "$REDIS_PASSWORD"
} > "$KVROCKS_DIR/kvrocks.conf"

exec kvrocks -c "$KVROCKS_DIR/kvrocks.conf" --dir "$KVROCKS_DIR"
