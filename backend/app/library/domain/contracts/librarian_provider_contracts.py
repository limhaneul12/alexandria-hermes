"""Librarian provider repository command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.event_enum.provider_enums import AuthType, ProviderType
from app.library.domain.types.librarian_provider_payload_types import (
    LibrarianProviderCreateRecord,
    LibrarianProviderUpdateRecord,
    LibrarianProviderUpdateValues,
)
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProviderCreate:
    """Fields required to persist a librarian provider."""

    name: str
    provider_type: ProviderType
    auth_type: AuthType
    enabled: bool
    config: JSONObject
    created_at: datetime
    updated_at: datetime

    def to_record(self) -> LibrarianProviderCreateRecord:
        """Return persistence fields for SQLAlchemy model construction.

        Returns:
            LibrarianProviderCreateRecord: Persistence record for provider creation.
        """
        record: LibrarianProviderCreateRecord = {
            "name": self.name,
            "provider_type": self.provider_type.value,
            "auth_type": self.auth_type.value,
            "enabled": self.enabled,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return record


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianProviderUpdate:
    """Patch fields for a librarian provider."""

    values: LibrarianProviderUpdateValues

    def to_record(self) -> LibrarianProviderUpdateRecord:
        """Return persistence fields for patching.

        Returns:
            LibrarianProviderUpdateRecord: Persistence record for provider patching.
        """
        record: LibrarianProviderUpdateRecord = {}
        if "name" in self.values:
            record["name"] = self.values["name"]
        if "provider_type" in self.values:
            record["provider_type"] = self.values["provider_type"].value
        if "auth_type" in self.values:
            record["auth_type"] = self.values["auth_type"].value
        if "enabled" in self.values:
            record["enabled"] = self.values["enabled"]
        if "config" in self.values:
            record["config"] = self.values["config"]
        return record
