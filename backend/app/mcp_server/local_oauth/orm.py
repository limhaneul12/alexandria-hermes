"""SQLAlchemy persistence models for self-hosted MCP OAuth state."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.types.extra_types import JSONObject


class McpOAuthClientORM(Base):
    """Dynamic OAuth client registration persisted for reconnects."""

    __tablename__ = "mcp_oauth_clients"

    client_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_secret_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_metadata: Mapped[JSONObject] = mapped_column(JSON, nullable=False)
    issued_at: Mapped[int] = mapped_column(Integer, nullable=False)
    secret_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class McpOAuthAuthorizationRequestORM(Base):
    """Pending authorization request awaiting local operator approval."""

    __tablename__ = "mcp_oauth_authorization_requests"

    request_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("mcp_oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(256), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_uri_provided_explicitly: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    approval_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class McpOAuthAuthorizationCodeORM(Base):
    """Hashed one-time authorization code state."""

    __tablename__ = "mcp_oauth_authorization_codes"

    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("mcp_oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(256), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_uri_provided_explicitly: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    consumed_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class McpOAuthTokenORM(Base):
    """Hashed access or refresh token in one revocable token family."""

    __tablename__ = "mcp_oauth_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("mcp_oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    revoked_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
