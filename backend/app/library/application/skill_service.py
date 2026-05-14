"""Skill-specific application services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.library.application.item_service import ItemService
from app.library.application.skills.item_commands import (
    SkillCreateFields,
    SkillItemCreateCommand,
    build_agent_skill_create_command,
    build_librarian_skill_create_command,
    build_user_skill_create_command,
)
from app.library.application.skills.payload_mapper import shape_skill_patch_payload
from app.library.domain.contracts.librarian_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.domain.types.item_payload_types import (
    LibraryItemListResult,
    LibraryItemPayload,
)
from app.library.domain.types.skill_payload_types import SkillSchemaPayload
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONObject, JSONValue


class SkillService:
    """Service for skill registration and generation workflows."""

    def __init__(self, item_service: ItemService) -> None:
        """Initialize service.

        Args:
            item_service: Shared item service.
        """
        self.item_service = item_service

    async def create_skill(
        self,
        title: str,
        summary: str | None,
        content: str,
        category_id: str | None,
        tags: list[str],
        purpose: str,
        input_schema: SkillSchemaPayload,
        output_schema: SkillSchemaPayload,
        usage_example: str | None,
        required_tools: list[str],
        risk_level: str,
        version: str,
        created_by_name: str,
        activate: bool = False,
        status: ItemStatus | None = None,
    ) -> LibraryItemPayload:
        """Create one user-submitted skill.

        Args:
            title: Skill title.
            summary: Optional summary.
            content: Long-form content.
            category_id: Optional category.
            tags: Tag list.
            purpose: Problem statement.
            input_schema: Input JSON schema.
            output_schema: Output JSON schema.
            usage_example: Example run.
            required_tools: Tool dependency names.
            risk_level: Risk label.
            version: Version text.
            created_by_name: Human-readable source identifier.
            activate: Whether to mark active.
            status: Desired initial status.

        Returns:
            Item payload.
        """
        command = build_user_skill_create_command(
            SkillCreateFields(
                title=title,
                summary=summary,
                content=content,
                category_id=category_id,
                tags=tags,
                purpose=purpose,
                input_schema=input_schema,
                output_schema=output_schema,
                usage_example=usage_example,
                required_tools=required_tools,
                risk_level=risk_level,
                version=version,
                created_by_name=created_by_name,
                activate=activate,
                status=status,
            )
        )
        created = await self._create_item_from_command(command)
        return created

    async def create_skill_by_agent(
        self,
        title: str,
        content: str,
        summary: str | None,
        category_id: str | None,
        tags: list[str],
        purpose: str,
        input_schema: SkillSchemaPayload,
        output_schema: SkillSchemaPayload,
        usage_example: str | None,
        required_tools: list[str],
        risk_level: str,
        version: str,
        created_by_name: str,
        activate: bool,
        status: ItemStatus | None = None,
    ) -> LibraryItemPayload:
        """Create skill payload from a structured agent candidate.

        Args:
            title: Candidate title.
            content: Content body.
            summary: Optional summary.
            category_id: Optional category.
            tags: Tag list.
            purpose: Skill purpose.
            input_schema: Input schema.
            output_schema: Output schema.
            usage_example: Example.
            required_tools: Tool list.
            risk_level: Risk level.
            version: Semantic version.
            created_by_name: Source name.
            activate: Whether to activate directly.
            status: Optional forced status.

        Returns:
            Item payload.
        """
        command = build_agent_skill_create_command(
            SkillCreateFields(
                title=title,
                summary=summary,
                content=content,
                category_id=category_id,
                tags=tags,
                purpose=purpose,
                input_schema=input_schema,
                output_schema=output_schema,
                usage_example=usage_example,
                required_tools=required_tools,
                risk_level=risk_level,
                version=version,
                created_by_name=created_by_name,
                activate=activate,
                status=status,
            )
        )
        created = await self._create_item_from_command(command)
        return created

    async def create_from_librarian_candidate(
        self,
        generated: CreateSkillCandidateResult,
        category_id: str | None,
        tags: list[str],
        created_by_name: str,
    ) -> LibraryItemPayload:
        """Create a librarian produced candidate into a library draft item.

        Args:
            generated: Candidate payload from provider adapter.
            category_id: Optional category.
            tags: Tag list.
            created_by_name: Source display name.

        Returns:
            Item payload.
        """
        command = build_librarian_skill_create_command(
            generated=generated,
            category_id=category_id,
            tags=tags,
            created_by_name=created_by_name,
        )
        created = await self._create_item_from_command(command)
        return created

    async def list_skills(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> LibraryItemListResult:
        """List skill items.

        Args:
            limit: Page size.
            offset: Page offset.

        Returns:
            Tuple of payload list and total.
        """
        return await self.item_service.list_items(
            item_type=ItemType.SKILL,
            limit=limit,
            offset=offset,
        )

    async def patch_skill(
        self,
        item_id: str,
        payload: Mapping[str, JSONValue],
    ) -> LibraryItemPayload:
        """Patch one skill item.

        Args:
            item_id: Target item id.
            payload: Patch payload map.

        Returns:
            Patched item payload.
        """
        item = await self.item_service.get_item(item_id)
        if item["item_type"] != ItemType.SKILL:
            raise ValidationError("Not a skill item")

        update_payload = shape_skill_patch_payload(item=item, payload=payload)
        updated = await self.item_service.update_item(
            item_id,
            payload=cast(dict[str, JSONValue], update_payload),
        )
        return updated

    async def _create_item_from_command(
        self,
        command: SkillItemCreateCommand,
    ) -> LibraryItemPayload:
        created = await self.item_service.create_item(
            item_type=command.item_type,
            title=command.title,
            summary=command.summary,
            content=command.content,
            category_id=command.category_id,
            tags=command.tags,
            status=command.status,
            source_type=command.source_type,
            created_by_type=command.created_by_type,
            created_by_name=command.created_by_name,
            details=cast(JSONObject, command.details),
        )
        return created
