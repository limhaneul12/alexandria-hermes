"""Pydantic contracts for maintenance MCP tool inputs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.types.extra_types import JSONObject


class MaintenanceEmbeddingReindexToolRequest(BaseModel):
    """Validated MCP input for a queued embedding reindex job."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
    )

    requested_by: str = Field(default="mcp", min_length=1, max_length=120)
    source_id: str = Field(default="manual", min_length=1, max_length=200)
    limit: int = Field(default=250, ge=1, le=1000)
    force: bool = False

    @field_validator("requested_by", "source_id")
    @classmethod
    def normalize_nonblank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    def to_payload(self) -> JSONObject:
        """Return the explicit backend request payload.

        Returns:
            JSON object accepted by the backend maintenance submission endpoint.
        """
        return {
            "requested_by": self.requested_by,
            "source_id": self.source_id,
            "limit": self.limit,
            "force": self.force,
        }


class MaintenanceJobIdToolRequest(BaseModel):
    """Validated MCP input for one maintenance job lookup."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1, max_length=128)

    @field_validator("job_id")
    @classmethod
    def normalize_job_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("job_id must not be blank")
        return normalized
