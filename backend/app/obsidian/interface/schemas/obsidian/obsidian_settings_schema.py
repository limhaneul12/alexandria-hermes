"""HTTP schemas for Obsidian runtime settings."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import ObsidianVaultSettingsUpdate
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


class ObsidianVaultSettingsUpdateRequest(StrictSchemaModel):
    """Request to change the backend Obsidian vault destination."""

    vault_path: str = Field(min_length=1)
    alexandria_root: str = Field(default=".", min_length=1)
    initialize: bool = True
    reindex: bool = True

    def to_command(self) -> ObsidianVaultSettingsUpdate:
        """Convert request into an application update command.

        Returns:
            Application vault settings update command.
        """
        return ObsidianVaultSettingsUpdate(
            vault_path=self.vault_path,
            alexandria_root=self.alexandria_root,
            initialize=self.initialize,
            reindex=self.reindex,
        )
