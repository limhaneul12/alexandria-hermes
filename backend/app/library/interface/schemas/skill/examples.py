"""JSON schema examples for skill API schemas."""

from __future__ import annotations

from pydantic.json_schema import JsonDict

SKILL_CREATE_EXAMPLE: JsonDict = {
    "title": "FastAPI dependency override",
    "summary": "Override narrow route dependencies in tests.",
    "content": "Use app.dependency_overrides with a fake service.",
    "category_id": "00000000-0000-4000-8000-000000000002",
    "tags": ["fastapi", "testing"],
    "purpose": "Test API routes without broad container coupling.",
    "input_schema": {
        "type": "object",
        "properties": {"route": {"type": "string"}},
    },
    "output_schema": {
        "type": "object",
        "properties": {"status": {"type": "string"}},
    },
    "usage_example": "Override the item_service container provider with a fake ItemService.",
    "required_tools": ["pytest"],
    "risk_level": "LOW",
    "version": "1.0.0",
    "created_by_name": "alex",
    "status": "DRAFT",
}

AGENT_SUBMIT_SKILL_EXAMPLE: JsonDict = {
    "title": "Agent-authored FastAPI skill",
    "purpose": "Capture route testing guidance.",
    "summary": "Generated candidate from an agent.",
    "content": "Use narrow dependency overrides.",
    "category_id": "00000000-0000-4000-8000-000000000002",
    "tags": ["agent", "fastapi"],
    "input_schema": {},
    "output_schema": {},
    "usage_example": "Submit, review, then activate.",
    "required_tools": ["pytest"],
    "risk_level": "LOW",
    "version": "1.0.0",
    "created_by_name": "research-agent",
    "activate": False,
    "status": "DRAFT",
}

SKILL_PATCH_EXAMPLE: JsonDict = {
    "summary": "Updated route testing guidance.",
    "status": "ACTIVE",
    "required_tools": ["pytest", "httpx"],
    "version": "1.0.1",
}

LIBRARIAN_SKILL_EXAMPLE: JsonDict = {
    "provider_id": "00000000-0000-4000-8000-000000000456",
    "prompt": "Create a skill for FastAPI dependency overrides.",
    "category_id": "00000000-0000-4000-8000-000000000002",
    "tags": ["fastapi"],
    "created_by_name": "alex",
}

SKILL_RESPONSE_EXAMPLE: JsonDict = {
    "id": "00000000-0000-4000-8000-000000000010",
    "item_type": "SKILL",
    "title": "FastAPI dependency override",
    "summary": "Override narrow route dependencies in tests.",
    "content": "Use app.dependency_overrides with a fake service.",
    "details": {
        "purpose": "Test API routes without broad container coupling.",
        "risk_level": "LOW",
    },
    "category_id": "00000000-0000-4000-8000-000000000002",
    "status": "ACTIVE",
    "source_type": "USER_CREATED",
    "created_by_type": "USER",
    "created_by_name": "alex",
}
