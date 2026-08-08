#!/bin/sh
set -eu

require_nonblank() {
  variable_name="$1"
  eval "variable_value=\${${variable_name}-}"
  case "${variable_value}" in
    *[![:space:]]*) ;;
    *)
      echo "${variable_name} must not be blank" >&2
      exit 1
      ;;
  esac
}

: "${ALEXANDRIA_NEO4J_PASSWORD:?ALEXANDRIA_NEO4J_PASSWORD is required}"
case "${ALEXANDRIA_NEO4J_PASSWORD}" in
  *[![:space:]]*) ;;
  *)
    echo "ALEXANDRIA_NEO4J_PASSWORD must not be blank" >&2
    exit 1
    ;;
esac

: "${ALEXANDRIA_NEO4J_HEAP_INITIAL_SIZE:?ALEXANDRIA_NEO4J_HEAP_INITIAL_SIZE is required}"
: "${ALEXANDRIA_NEO4J_HEAP_MAX_SIZE:?ALEXANDRIA_NEO4J_HEAP_MAX_SIZE is required}"
: "${ALEXANDRIA_NEO4J_PAGECACHE_SIZE:?ALEXANDRIA_NEO4J_PAGECACHE_SIZE is required}"
: "${ALEXANDRIA_NEO4J_TX_LOG_ROTATION_SIZE:?ALEXANDRIA_NEO4J_TX_LOG_ROTATION_SIZE is required}"
: "${ALEXANDRIA_NEO4J_TX_LOG_RETENTION_POLICY:?ALEXANDRIA_NEO4J_TX_LOG_RETENTION_POLICY is required}"

for variable_name in \
  ALEXANDRIA_NEO4J_HEAP_INITIAL_SIZE \
  ALEXANDRIA_NEO4J_HEAP_MAX_SIZE \
  ALEXANDRIA_NEO4J_PAGECACHE_SIZE \
  ALEXANDRIA_NEO4J_TX_LOG_ROTATION_SIZE \
  ALEXANDRIA_NEO4J_TX_LOG_RETENTION_POLICY
do
  require_nonblank "${variable_name}"
done

export NEO4J_AUTH="neo4j/${ALEXANDRIA_NEO4J_PASSWORD}"
export NEO4J_server_memory_heap_initial__size="${ALEXANDRIA_NEO4J_HEAP_INITIAL_SIZE}"
export NEO4J_server_memory_heap_max__size="${ALEXANDRIA_NEO4J_HEAP_MAX_SIZE}"
export NEO4J_server_memory_pagecache_size="${ALEXANDRIA_NEO4J_PAGECACHE_SIZE}"
export NEO4J_db_tx__log_rotation_size="${ALEXANDRIA_NEO4J_TX_LOG_ROTATION_SIZE}"
export NEO4J_db_tx__log_rotation_retention__policy="${ALEXANDRIA_NEO4J_TX_LOG_RETENTION_POLICY}"

exec /startup/docker-entrypoint.sh neo4j
