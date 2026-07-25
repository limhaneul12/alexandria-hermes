"""HTTP schemas for Obsidian vault inventory operations."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianVaultInventoryRequest,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianVaultInventoryItem,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


class ObsidianVaultInventoryRequestSchema(StrictSchemaModel):
    """Request to inventory managed Obsidian notes under one scope."""

    scope_path: str | None = None

    def to_command(self) -> ObsidianVaultInventoryRequest:
        """Convert request into application command.

        Returns:
            Application inventory request.
        """
        return ObsidianVaultInventoryRequest(scope_path=self.scope_path)


class ObsidianVaultInventoryItemResponse(StrictSchemaModel):
    """One managed note inventory item."""

    id: str
    path: str
    alexandria_type: AlexandriaNoteType
    title: str
    status: str
    tags: list[str]
    project: str | None
    size_bytes: int
    modified_at: AwareTimestamp

    @classmethod
    def from_entity(
        cls,
        item: ObsidianVaultInventoryItem,
    ) -> ObsidianVaultInventoryItemResponse:
        """Create response from inventory item.

        Args:
            item: Inventory item entity.

        Returns:
            HTTP inventory item.
        """
        return cls(
            id=item.note_id,
            path=item.relative_path,
            alexandria_type=item.alexandria_type,
            title=item.title,
            status=item.status,
            tags=item.tags,
            project=item.project,
            size_bytes=item.size_bytes,
            modified_at=item.modified_at,
        )


class ObsidianVaultInventoryResponse(StrictSchemaModel):
    """Inventory response."""

    items: list[ObsidianVaultInventoryItemResponse]
    total: int
