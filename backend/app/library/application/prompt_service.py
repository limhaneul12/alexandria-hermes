"""Prompt-specific application services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.library.application.item_service import ItemService
from app.library.application.prompts.payload_mapper import (
    build_prompt_details,
    shape_prompt_patch_payload,
)
from app.library.application.quality_gate import run_library_quality_gate
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.prompt_enums import (
    PromptContentFormat,
    PromptDomain,
    PromptKind,
    PromptTaskType,
)
from app.library.domain.types.item_payload_types import (
    LibraryItemListResult,
    LibraryItemPayload,
)
from app.library.domain.types.prompt_payload_types import PromptVariablePayload
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONObject, JSONValue


class PromptService:
    """Service for prompt registration and update workflows."""

    def __init__(self, item_service: ItemService) -> None:
        """Initialize service.

        Args:
            item_service: Shared item service.
        """
        self.item_service = item_service

    async def create_prompt(
        self,
        title: str,
        summary: str | None,
        content: str,
        category_id: str | None,
        tags: list[str],
        content_format: PromptContentFormat,
        prompt_kind: PromptKind,
        prompt_domain: PromptDomain,
        prompt_task_type: PromptTaskType,
        input_variables: list[PromptVariablePayload],
        output_format: str | None,
        target_actor: str | None,
        target_model_family: str | None,
        language: str | None,
        related_item_ids: list[str],
        safety_notes: str | None,
        version: str,
        change_summary: str | None,
        created_by_name: str,
        created_by_type: CreatedByType,
        source_type: SourceType,
        status: ItemStatus,
    ) -> LibraryItemPayload:
        """Create one prompt library item.

        Args:
            title: Prompt title.
            summary: Optional summary.
            content: Prompt body.
            category_id: Optional category.
            tags: Tag list.
            content_format: Body syntax.
            prompt_kind: Prompt usage position.
            prompt_domain: Business domain.
            prompt_task_type: Task classification.
            input_variables: Template variables.
            output_format: Optional output guidance.
            target_actor: Optional actor.
            target_model_family: Optional model family.
            language: Optional language hint.
            related_item_ids: Related item ids.
            safety_notes: Optional safety notes.
            version: Version text.
            change_summary: Optional change summary.
            created_by_name: Creator display name.
            created_by_type: Creator type.
            source_type: Source type.
            status: Item status.

        Returns:
            Created item payload.
        """
        gate = run_library_quality_gate(
            item_type=ItemType.PROMPT,
            title=title,
            content=content,
        )
        safe_content = gate.redacted_content
        details = build_prompt_details(
            title=title,
            content=safe_content,
            content_format=content_format,
            prompt_kind=prompt_kind,
            prompt_domain=prompt_domain,
            prompt_task_type=prompt_task_type,
            input_variables=input_variables,
            output_format=output_format,
            target_actor=target_actor,
            target_model_family=target_model_family,
            language=language,
            related_item_ids=related_item_ids,
            safety_notes=safety_notes,
            version=version,
            change_summary=change_summary,
        )
        created = await self.item_service.create_item(
            item_type=ItemType.PROMPT,
            title=title,
            summary=summary,
            content=safe_content,
            category_id=category_id,
            tags=tags,
            status=status,
            source_type=source_type,
            created_by_type=created_by_type,
            created_by_name=created_by_name,
            details=cast(JSONObject, details),
        )
        return created

    async def list_prompts(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> LibraryItemListResult:
        """List prompt items.

        Args:
            limit: Page size.
            offset: Page offset.

        Returns:
            Tuple of payload list and total.
        """
        result = await self.item_service.list_items(
            item_type=ItemType.PROMPT,
            limit=limit,
            offset=offset,
        )
        return result

    async def patch_prompt(
        self,
        item_id: str,
        payload: Mapping[str, JSONValue],
    ) -> LibraryItemPayload:
        """Patch one prompt item.

        Args:
            item_id: Target item id.
            payload: Patch payload map.

        Returns:
            Patched item payload.
        """
        item = await self.item_service.get_item(item_id)
        if item["item_type"] != ItemType.PROMPT:
            raise ValidationError("Not a prompt item")
        update_payload = shape_prompt_patch_payload(item=item, payload=payload)
        updated = await self.item_service.update_item(
            item_id,
            payload=cast(dict[str, JSONValue], update_payload),
        )
        return updated
