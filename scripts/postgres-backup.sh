#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_CONTAINER="${ALEXANDRIA_POSTGRES_CONTAINER:-alexandria-postgres}"
BACKUP_ROOT="${ALEXANDRIA_POSTGRES_BACKUP_ROOT:-${ROOT_DIR}/backups/postgres}"
BACKUP_PASSPHRASE="${ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE:-}"

fail() {
  printf 'postgres backup failed: %s\n' "$1" >&2
  exit 1
}

[[ -n "${BACKUP_PASSPHRASE}" ]] || fail "set ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE"
command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v openssl >/dev/null 2>&1 || fail "openssl is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"

docker inspect "${POSTGRES_CONTAINER}" >/dev/null 2>&1 \
  || fail "container ${POSTGRES_CONTAINER} does not exist"
[[ "$(docker inspect -f '{{.State.Running}}' "${POSTGRES_CONTAINER}")" == "true" ]] \
  || fail "container ${POSTGRES_CONTAINER} is not running"

POSTGRES_USER="$(
  docker exec "${POSTGRES_CONTAINER}" sh -eu -c \
    'printf %s "${POSTGRES_USER:-postgres}"'
)"
POSTGRES_DB="$(
  docker exec "${POSTGRES_CONTAINER}" sh -eu -c \
    'printf %s "${POSTGRES_DB:-${POSTGRES_USER:-postgres}}"'
)"
[[ -n "${POSTGRES_DB}" && -n "${POSTGRES_USER}" ]] \
  || fail "container PostgreSQL identity is unavailable"

SOURCE_REVISION="$(docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  database_name="${POSTGRES_DB:-$database_user}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$database_name" \
    --command="SELECT version_num FROM alembic_version"
')"
SOURCE_TABLE_COUNT="$(docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  database_name="${POSTGRES_DB:-$database_user}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$database_name" \
    --command="SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\''"
')"
SOURCE_VECTOR_EXTENSION="$(docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  database_name="${POSTGRES_DB:-$database_user}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$database_name" \
    --command="SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = '\''vector'\'')"
')"
[[ -n "${SOURCE_REVISION}" ]] || fail "source database has no Alembic revision"
[[ "${SOURCE_TABLE_COUNT}" =~ ^[0-9]+$ && "${SOURCE_TABLE_COUNT}" -gt 0 ]] \
  || fail "source database has no public tables"
[[ "${SOURCE_VECTOR_EXTENSION}" == "t" ]] \
  || fail "source database does not have the pgvector extension"

BACKUP_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
FINAL_ROOT="${BACKUP_ROOT}/${BACKUP_ID}"
TEMPORARY_ROOT="${BACKUP_ROOT}/.${BACKUP_ID}.tmp"
ARCHIVE_PATH="${TEMPORARY_ROOT}/database.dump"
ENCRYPTED_PATH="${TEMPORARY_ROOT}/database.dump.enc"
MANIFEST_PATH="${TEMPORARY_ROOT}/manifest.json"

[[ ! -e "${FINAL_ROOT}" && ! -e "${TEMPORARY_ROOT}" ]] \
  || fail "backup destination already exists"
mkdir -p "${TEMPORARY_ROOT}"
chmod 700 "${TEMPORARY_ROOT}"

cleanup() {
  rm -f "${ARCHIVE_PATH}"
  if [[ -d "${TEMPORARY_ROOT}" ]]; then
    rm -rf "${TEMPORARY_ROOT}"
  fi
}
trap cleanup EXIT

docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  database_name="${POSTGRES_DB:-$database_user}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-acl \
    --username="$database_user" \
    --dbname="$database_name"
' >"${ARCHIVE_PATH}"

[[ -s "${ARCHIVE_PATH}" ]] || fail "pg_dump produced an empty archive"
docker exec -i "${POSTGRES_CONTAINER}" pg_restore --list \
  <"${ARCHIVE_PATH}" >/dev/null

ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE="${BACKUP_PASSPHRASE}" \
  openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 \
    -pass env:ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE \
    -in "${ARCHIVE_PATH}" \
    -out "${ENCRYPTED_PATH}"
chmod 600 "${ENCRYPTED_PATH}"

PLAINTEXT_SHA256="$(shasum -a 256 "${ARCHIVE_PATH}" | awk '{print $1}')"
ENCRYPTED_SHA256="$(shasum -a 256 "${ENCRYPTED_PATH}" | awk '{print $1}')"
ENCRYPTED_BYTES="$(wc -c <"${ENCRYPTED_PATH}" | tr -d ' ')"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

python3 - \
  "${MANIFEST_PATH}" \
  "${BACKUP_ID}" \
  "${CREATED_AT}" \
  "${POSTGRES_CONTAINER}" \
  "${POSTGRES_DB}" \
  "${POSTGRES_USER}" \
  "${SOURCE_REVISION}" \
  "${SOURCE_TABLE_COUNT}" \
  "${SOURCE_VECTOR_EXTENSION}" \
  "${PLAINTEXT_SHA256}" \
  "${ENCRYPTED_SHA256}" \
  "${ENCRYPTED_BYTES}" <<'PY'
import json
import sys
from pathlib import Path

(
    manifest_path,
    backup_id,
    created_at,
    container,
    database,
    database_user,
    source_revision,
    public_table_count,
    vector_extension,
    plaintext_sha256,
    encrypted_sha256,
    encrypted_bytes,
) = sys.argv[1:]
payload = {
    "schema_version": 2,
    "backup_id": backup_id,
    "created_at": created_at,
    "container": container,
    "database": database,
    "database_user": database_user,
    "source_revision": source_revision.strip(),
    "public_table_count": int(public_table_count.strip()),
    "vector_extension_present": vector_extension.strip().lower() == "t",
    "archive_format": "pg_dump-custom",
    "encryption": "openssl-aes-256-cbc-pbkdf2-iter-200000",
    "archive_path": "database.dump.enc",
    "plaintext_sha256": plaintext_sha256,
    "encrypted_sha256": encrypted_sha256,
    "encrypted_bytes": int(encrypted_bytes),
}
Path(manifest_path).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
chmod 600 "${MANIFEST_PATH}"

rm -f "${ARCHIVE_PATH}"
mv "${TEMPORARY_ROOT}" "${FINAL_ROOT}"
trap - EXIT

printf '%s\n' "${FINAL_ROOT}"
