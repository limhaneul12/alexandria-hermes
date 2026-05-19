"""Application service for librarian operation endpoints."""

from __future__ import annotations

from app.librarian.application.candidate_generator import build_candidate_stub
from app.librarian.domain.types.librarian_ops_payload_types import (
    LibrarianClassificationPayload,
)
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.item_payload_types import LibraryItemPayload
from app.shared.types.extra_types import JSONObject
from app.shared.types.types_convert_utils import now_utc


class LibrarianOpsService:
    """Own lightweight librarian operation policies outside HTTP routers."""

    def classify(self, text: str) -> LibrarianClassificationPayload:
        """Classify prompt text into the library taxonomy.

        Args:
            text: User text to classify.

        Returns:
            LibrarianClassificationPayload: Taxonomy label and confidence.
        """
        lowered = text.lower()
        if "api" in lowered or "agent" in lowered:
            return {"label": ItemType.SKILL, "confidence": 0.83}
        return {"label": ItemType.KNOWLEDGE, "confidence": 0.55}

    def generate_skill_candidate(
        self,
        provider_id: str,
        prompt: str,
        category_id: str | None,
    ) -> LibraryItemPayload:
        """Generate a draft skill candidate response without persistence.

        Args:
            provider_id: Librarian provider identifier used for generation.
            prompt: Candidate generation prompt.
            category_id: Optional library category assigned by the caller.

        Returns:
            LibraryItemPayload: Draft skill candidate shaped as an item payload.
        """
        candidate = build_candidate_stub(provider_id=provider_id, prompt=prompt)
        candidate_payload = candidate.to_candidate_payload()
        now = now_utc()
        details: JSONObject = {
            "purpose": candidate_payload["purpose"],
            "input_schema": candidate_payload["input_schema"],
            "output_schema": candidate_payload["output_schema"],
            "required_tools": candidate_payload["required_tools"],
            "risk_level": candidate_payload["risk_level"],
            "version": candidate_payload["version"],
        }
        payload: LibraryItemPayload = {
            "id": "draft-skill-candidate",
            "item_type": ItemType.SKILL,
            "title": candidate_payload["title"],
            "summary": candidate_payload["summary"],
            "content": candidate_payload["content"],
            "category_id": category_id,
            "tags": ["draft", "librarian"],
            "details": details,
            "status": ItemStatus.DRAFT,
            "source_type": SourceType.LIBRARIAN_CREATED,
            "created_by_type": CreatedByType.LIBRARIAN,
            "created_by_name": "librarian",
            "created_at": now,
            "updated_at": now,
        }
        return payload
