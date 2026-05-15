"""Connection provider read models returned by repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True)
class LibrarianProvider:
    """Read model for external provider/connection configuration."""

    id: str
    name: str
    provider_type: str
    auth_type: str
    enabled: bool
    config: JSONObject
    created_at: datetime
    updated_at: datetime
