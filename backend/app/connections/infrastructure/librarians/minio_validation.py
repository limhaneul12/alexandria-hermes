"""MINIO librarian provider validation."""

from __future__ import annotations

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.infrastructure.librarians.contracts import ProviderClientTestResult


def test_minio_provider(
    *,
    provider: LibrarianProvider,
    api_key: str,
) -> ProviderClientTestResult:
    """Validate MINIO provider settings without exposing credential material.

    Args:
        provider [LibrarianProvider]: Value supplied to test_minio_provider.
        api_key [str]: Value supplied to test_minio_provider.

    Returns:
        ProviderClientTestResult: Value produced by test_minio_provider.
    """
    endpoint = provider.config.get("endpoint")
    bucket = provider.config.get("bucket")
    if not isinstance(endpoint, str) or not endpoint.strip():
        result = ProviderClientTestResult(
            provider_id=provider.id,
            ok=False,
            message="MINIO endpoint missing",
        )
        return result
    if not isinstance(bucket, str) or not bucket.strip():
        result = ProviderClientTestResult(
            provider_id=provider.id,
            ok=False,
            message="MINIO bucket missing",
        )
        return result
    access_key, separator, secret_key = api_key.partition(":")
    if not separator or not access_key.strip() or not secret_key.strip():
        result = ProviderClientTestResult(
            provider_id=provider.id,
            ok=False,
            message="MINIO credential must be access_key:secret_key",
        )
        return result
    result = ProviderClientTestResult(
        provider_id=provider.id,
        ok=True,
        message="MINIO settings accepted for object listing",
    )
    return result
