#!/bin/sh
set -eu

: "${ALEXANDRIA_REDIS_MAXMEMORY:?ALEXANDRIA_REDIS_MAXMEMORY is required}"
case "${ALEXANDRIA_REDIS_MAXMEMORY}" in
  *[![:space:]]*) ;;
  *)
    echo "ALEXANDRIA_REDIS_MAXMEMORY must not be blank" >&2
    exit 1
    ;;
esac

exec /usr/local/bin/docker-entrypoint.sh redis-server \
  --save "" \
  --appendonly yes \
  --appendfsync everysec \
  --maxmemory "${ALEXANDRIA_REDIS_MAXMEMORY}" \
  --maxmemory-policy noeviction
