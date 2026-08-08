"""Provider credential migration contracts."""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "migrations" / "versions" / "202608070100_credential_payload_text.py"
)


def test_provider_credential_migration_is_lossless_and_fail_closed() -> None:
    """Large encrypted payloads are preserved and lossy downgrade is rejected."""
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "202608070100_credential_text"' in source
    assert 'down_revision: str | None = "202608062130_pg_search"' in source
    assert "type_=sa.Text()" in source
    assert "length(value) > :maximum_length" in source
    assert "cannot downgrade librarian_provider_secrets.value" in source
