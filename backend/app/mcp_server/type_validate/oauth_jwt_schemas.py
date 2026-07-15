"""Pydantic schemas for validating OAuth JWT/JWKS payloads."""

from __future__ import annotations

from pydantic import Field

from app.mcp_server.type_validate.auth_contracts import JwtAlgorithm
from app.shared.schemas.common_schemas import StrictSchemaModel


class JwtHeaderPayload(StrictSchemaModel):
    """Validated JWT JOSE header fields used by the MCP verifier."""

    alg: JwtAlgorithm
    kid: str


class JwtClaimsPayload(StrictSchemaModel):
    """Validated JWT claim fields required by the MCP resource server."""

    iss: str
    aud: str | tuple[str, ...]
    exp: int
    nbf: int | None = None
    scope: str | None = None
    scp: tuple[str, ...] | None = None


class RsaJsonWebKeyPayload(StrictSchemaModel):
    """Validated RSA JWK used to verify RS256 bearer tokens."""

    kty: str = Field(pattern="^RSA$")
    kid: str
    n: str
    e: str
    alg: JwtAlgorithm | None = None
    use: str | None = None


class JsonWebKeySetPayload(StrictSchemaModel):
    """Validated JWKS response."""

    keys: tuple[RsaJsonWebKeyPayload, ...]
