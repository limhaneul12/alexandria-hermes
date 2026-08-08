#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_CONTAINER="${ALEXANDRIA_POSTGRES_CONTAINER:-alexandria-postgres}"
BACKUP_ROOT="${ALEXANDRIA_POSTGRES_BACKUP_ROOT:-${ROOT_DIR}/backups/postgres}"
BACKUP_PASSPHRASE="${ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE:-}"
BACKUP_REFERENCE="${1:-}"

fail() {
  printf 'postgres restore drill failed: %s\n' "$1" >&2
  exit 1
}

[[ -n "${BACKUP_REFERENCE}" ]] || fail "pass a backup id or backup directory"
[[ -n "${BACKUP_PASSPHRASE}" ]] || fail "set ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE"
command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v openssl >/dev/null 2>&1 || fail "openssl is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"

if [[ -d "${BACKUP_REFERENCE}" ]]; then
  BACKUP_DIR="$(cd "${BACKUP_REFERENCE}" && pwd)"
else
  BACKUP_DIR="${BACKUP_ROOT}/${BACKUP_REFERENCE}"
fi
MANIFEST_PATH="${BACKUP_DIR}/manifest.json"
[[ -f "${MANIFEST_PATH}" ]] || fail "manifest.json is missing"

docker inspect "${POSTGRES_CONTAINER}" >/dev/null 2>&1 \
  || fail "container ${POSTGRES_CONTAINER} does not exist"
[[ "$(docker inspect -f '{{.State.Running}}' "${POSTGRES_CONTAINER}")" == "true" ]] \
  || fail "container ${POSTGRES_CONTAINER} is not running"

MANIFEST_VALUES="$(python3 - "${MANIFEST_PATH}" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = (
    "backup_id",
    "archive_path",
    "plaintext_sha256",
    "encrypted_sha256",
    "database",
)
missing = [key for key in required if not isinstance(manifest.get(key), str)]
if missing:
    raise SystemExit("invalid manifest fields: " + ", ".join(missing))
schema_version = manifest.get("schema_version", 1)
if not isinstance(schema_version, int) or schema_version < 1:
    raise SystemExit("invalid manifest schema_version")
source_revision = manifest.get("source_revision", "")
public_table_count = manifest.get("public_table_count", 0)
vector_extension_present = manifest.get("vector_extension_present", False)
if source_revision and not isinstance(source_revision, str):
    raise SystemExit("invalid manifest source_revision")
if not isinstance(public_table_count, int) or public_table_count < 0:
    raise SystemExit("invalid manifest public_table_count")
if not isinstance(vector_extension_present, bool):
    raise SystemExit("invalid manifest vector_extension_present")
for key in required:
    print(manifest[key])
print(source_revision)
print(public_table_count)
print("true" if vector_extension_present else "false")
PY
)"
BACKUP_ID="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '1p')"
ARCHIVE_NAME="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '2p')"
EXPECTED_PLAINTEXT_SHA256="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '3p')"
EXPECTED_ENCRYPTED_SHA256="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '4p')"
SOURCE_DATABASE="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '5p')"
EXPECTED_SOURCE_REVISION="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '6p')"
EXPECTED_PUBLIC_TABLE_COUNT="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '7p')"
EXPECTED_VECTOR_EXTENSION="$(printf '%s\n' "${MANIFEST_VALUES}" | sed -n '8p')"
ENCRYPTED_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}"
[[ -f "${ENCRYPTED_PATH}" ]] || fail "encrypted archive is missing"

ACTUAL_ENCRYPTED_SHA256="$(shasum -a 256 "${ENCRYPTED_PATH}" | awk '{print $1}')"
[[ "${ACTUAL_ENCRYPTED_SHA256}" == "${EXPECTED_ENCRYPTED_SHA256}" ]] \
  || fail "encrypted archive checksum mismatch"

TEMPORARY_ARCHIVE="$(mktemp "${TMPDIR:-/tmp}/alexandria-postgres-drill.XXXXXX")"
DRILL_DATABASE="alexandria_restore_drill_$(date -u +%Y%m%d%H%M%S)_$$"
DRILL_CREATED=0

drop_drill_database() {
  docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
    database_user="${POSTGRES_USER:-postgres}"
    PGPASSWORD="$POSTGRES_PASSWORD" exec dropdb \
      --if-exists \
      --force \
      --username="$database_user" \
      "$1"
  ' sh "${DRILL_DATABASE}"
}

cleanup() {
  rm -f "${TEMPORARY_ARCHIVE}"
  if [[ "${DRILL_CREATED}" == "1" ]]; then
    drop_drill_database >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE="${BACKUP_PASSPHRASE}" \
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -pass env:ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE \
    -in "${ENCRYPTED_PATH}" \
    -out "${TEMPORARY_ARCHIVE}"

ACTUAL_PLAINTEXT_SHA256="$(shasum -a 256 "${TEMPORARY_ARCHIVE}" | awk '{print $1}')"
[[ "${ACTUAL_PLAINTEXT_SHA256}" == "${EXPECTED_PLAINTEXT_SHA256}" ]] \
  || fail "decrypted archive checksum mismatch"
docker exec -i "${POSTGRES_CONTAINER}" pg_restore --list \
  <"${TEMPORARY_ARCHIVE}" >/dev/null

docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec createdb \
    --template=template0 \
    --encoding=UTF8 \
    --username="$database_user" \
    "$1"
' sh "${DRILL_DATABASE}"
DRILL_CREATED=1

docker exec -i "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec pg_restore \
    --exit-on-error \
    --no-owner \
    --no-acl \
    --username="$database_user" \
    --dbname="$1"
' sh "${DRILL_DATABASE}" <"${TEMPORARY_ARCHIVE}"

REVISION="$(docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$1" \
    --command="SELECT version_num FROM alembic_version"
' sh "${DRILL_DATABASE}")"
TABLE_COUNT="$(docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$1" \
    --command="SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\''"
' sh "${DRILL_DATABASE}")"
VECTOR_EXTENSION="$(docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$1" \
    --command="SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = '\''vector'\'')"
' sh "${DRILL_DATABASE}")"

[[ -n "${REVISION}" ]] || fail "restored database has no Alembic revision"
[[ "${TABLE_COUNT}" =~ ^[0-9]+$ && "${TABLE_COUNT}" -gt 0 ]] \
  || fail "restored database has no public tables"
[[ "${VECTOR_EXTENSION}" == "t" ]] \
  || fail "restored database does not have the pgvector extension"
if [[ -n "${EXPECTED_SOURCE_REVISION}" ]]; then
  [[ "${REVISION}" == "${EXPECTED_SOURCE_REVISION}" ]] \
    || fail "restored Alembic revision does not match the backup manifest"
fi
if [[ "${EXPECTED_PUBLIC_TABLE_COUNT}" -gt 0 ]]; then
  [[ "${TABLE_COUNT}" == "${EXPECTED_PUBLIC_TABLE_COUNT}" ]] \
    || fail "restored public table count does not match the backup manifest"
fi
if [[ "${EXPECTED_VECTOR_EXTENSION}" == "true" ]]; then
  [[ "${VECTOR_EXTENSION}" == "t" ]] \
    || fail "restored pgvector state does not match the backup manifest"
fi

drop_drill_database
if docker exec "${POSTGRES_CONTAINER}" sh -eu -c '
  database_user="${POSTGRES_USER:-postgres}"
  database_name="${POSTGRES_DB:-$database_user}"
  PGPASSWORD="$POSTGRES_PASSWORD" exec psql \
    --no-psqlrc \
    --tuples-only \
    --no-align \
    --username="$database_user" \
    --dbname="$database_name" \
    --list
' | cut -d'|' -f1 | grep -Fxq "${DRILL_DATABASE}"; then
  fail "temporary restore database still exists after drop"
fi
DRILL_CREATED=0

REPORT_PATH="${BACKUP_DIR}/restore-drill-$(date -u +%Y%m%dT%H%M%SZ).json"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "${REPORT_PATH}" "${BACKUP_ID}" "${CREATED_AT}" \
  "${POSTGRES_CONTAINER}" "${SOURCE_DATABASE}" "${REVISION}" \
  "${TABLE_COUNT}" "${VECTOR_EXTENSION}" "${EXPECTED_SOURCE_REVISION}" \
  "${EXPECTED_PUBLIC_TABLE_COUNT}" <<'PY'
import json
import sys
from pathlib import Path

(
    report_path,
    backup_id,
    created_at,
    container,
    source_database,
    revision,
    table_count,
    vector_extension,
    expected_revision,
    expected_table_count,
) = sys.argv[1:]
payload = {
    "schema_version": 2,
    "status": "VERIFIED",
    "backup_id": backup_id,
    "created_at": created_at,
    "container": container,
    "source_database": source_database,
    "restored_revision": revision.strip(),
    "expected_revision": expected_revision.strip() or None,
    "revision_matches_manifest": (
        not expected_revision.strip() or revision.strip() == expected_revision.strip()
    ),
    "public_table_count": int(table_count.strip()),
    "expected_public_table_count": (
        int(expected_table_count.strip()) if int(expected_table_count.strip()) > 0 else None
    ),
    "table_count_matches_manifest": (
        int(expected_table_count.strip()) <= 0
        or int(table_count.strip()) == int(expected_table_count.strip())
    ),
    "vector_extension_present": vector_extension.strip().lower() == "t",
    "temporary_database_removed": True,
}
Path(report_path).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
chmod 600 "${REPORT_PATH}"

cleanup
trap - EXIT
printf '%s\n' "${REPORT_PATH}"
