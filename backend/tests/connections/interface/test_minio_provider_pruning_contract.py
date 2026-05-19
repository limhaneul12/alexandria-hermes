"""Contracts proving object storage is not a librarian provider type."""

from __future__ import annotations

import pytest
from app.connections.domain.event_enum.provider_enums import ProviderType
from app.connections.interface.schemas.librarian.provider_schema import (
    LibrarianProviderCreateRequest,
    LibrarianProviderPatchRequest,
)
from pydantic import ValidationError


def test_provider_type_excludes_minio() -> None:
    """Librarian providers should only include actual agent/model delegates."""
    provider_type_values = {provider_type.value for provider_type in ProviderType}

    assert provider_type_values == {"OPENAI", "OPENAI_CODEX"}


@pytest.mark.parametrize(
    "request_model",
    [LibrarianProviderCreateRequest, LibrarianProviderPatchRequest],
)
def test_librarian_provider_requests_reject_minio(request_model: type) -> None:
    """Settings connections must not accept object storage as a librarian provider."""
    payload = {
        "name": "team-minio",
        "provider_type": "MINIO",
        "auth_type": "API_KEY",
        "enabled": True,
        "config": {"endpoint": "https://objects.example.com", "bucket": "archive"},
        "api_key": "test-key",
    }

    with pytest.raises(ValidationError):
        request_model.model_validate(payload)
