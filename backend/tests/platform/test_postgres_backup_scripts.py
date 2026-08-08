"""PostgreSQL backup and restore-drill script contracts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKUP_SCRIPT = REPOSITORY_ROOT / "scripts/postgres-backup.sh"
RESTORE_DRILL_SCRIPT = REPOSITORY_ROOT / "scripts/postgres-restore-drill.sh"


def test_postgres_backup_scripts_are_executable_and_parse_as_bash() -> None:
    """Tracked operational scripts should remain directly executable and valid Bash."""
    for script in (BACKUP_SCRIPT, RESTORE_DRILL_SCRIPT):
        assert os.access(script, os.X_OK)
        completed = subprocess.run(
            ["/bin/bash", "-n", str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr


def test_postgres_backup_encrypts_and_validates_pg_dump_archive() -> None:
    """Backup should use server-version tools, archive validation, and encryption."""
    script = BACKUP_SCRIPT.read_text(encoding="utf-8")

    assert "docker exec" in script
    assert "pg_dump" in script
    assert "--format=custom" in script
    assert "--no-owner" in script
    assert "--no-acl" in script
    assert "pg_restore --list" in script
    assert "openssl enc -aes-256-cbc" in script
    assert "-pbkdf2" in script
    assert "ALEXANDRIA_POSTGRES_BACKUP_PASSPHRASE" in script
    assert "plaintext_sha256" in script
    assert "encrypted_sha256" in script
    assert '"schema_version": 2' in script
    assert '"source_revision"' in script
    assert '"public_table_count"' in script
    assert '"vector_extension_present"' in script
    assert "source database has no Alembic revision" in script
    assert "source database does not have the pgvector extension" in script
    assert "POSTGRES_PASSWORD=" not in script


def test_postgres_restore_drill_never_targets_the_live_database() -> None:
    """Restore drill should create and remove a distinct temporary database."""
    script = RESTORE_DRILL_SCRIPT.read_text(encoding="utf-8")

    assert "alexandria_restore_drill_" in script
    assert "createdb" in script
    assert "pg_restore" in script
    assert "--exit-on-error" in script
    assert "dropdb" in script
    assert "--force" in script
    assert "SELECT version_num FROM alembic_version" in script
    assert "information_schema.tables" in script
    assert "pg_extension" in script
    assert "EXPECTED_SOURCE_REVISION" in script
    assert "EXPECTED_PUBLIC_TABLE_COUNT" in script
    assert "restored Alembic revision does not match" in script
    assert "restored public table count does not match" in script
    assert "restored database does not have the pgvector extension" in script
    assert "temporary restore database still exists after drop" in script
    assert 'SOURCE_DATABASE="' in script
    assert '--dbname="$SOURCE_DATABASE"' not in script
    assert script.index("drop_drill_database\nif docker exec") < script.index(
        '"temporary_database_removed": True'
    )
