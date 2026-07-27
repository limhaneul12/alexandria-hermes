"""Self-hosted OAuth authorization provider for the MCP HTTP endpoint."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import TypeAdapter

from app.mcp_server.local_oauth.contracts import (
    LocalOAuthAuthorizationRequestRecord,
    LocalOAuthPairingCode,
    LocalOAuthTokenKind,
)
from app.mcp_server.local_oauth.repository import LocalMcpOAuthRepository
from app.shared.security.secret_cipher import SecretCipher
from app.shared.types.extra_types import JSONObject

_JSON_OBJECT_ADAPTER = TypeAdapter(JSONObject)


@dataclass(frozen=True, slots=True)
class LocalMcpOAuthSettings:
    """Security and expiry policy for one local MCP authorization server."""

    issuer_url: str
    resource_url: str
    required_scopes: tuple[str, ...]
    default_scopes: tuple[str, ...]
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    authorization_code_ttl_seconds: int
    approval_ttl_seconds: int
    pairing_code_ttl_seconds: int
    max_approval_attempts: int
    approval_key: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class LocalOAuthApprovalError(Exception):
    """Safe approval failure without exposing operator credentials."""

    status_code: int
    detail: str


class LocalMcpOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """Issue, rotate, verify, and revoke opaque MCP OAuth credentials.

    The public method count mirrors the MCP SDK provider protocol plus the local
    approval use case. Persistence and cryptographic storage remain delegated to
    focused collaborators.
    """

    def __init__(
        self,
        *,
        repository: LocalMcpOAuthRepository,
        secret_cipher: SecretCipher,
        settings: LocalMcpOAuthSettings,
    ) -> None:
        """Create the local OAuth provider.

        Args:
            repository: Durable OAuth state repository.
            secret_cipher: AES-GCM cipher for dynamic client secrets.
            settings: OAuth endpoint and expiry policy.
        """
        self._repository = repository
        self._secret_cipher = secret_cipher
        self._settings = settings

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Load one registered OAuth client.

        Args:
            client_id: Value supplied to get_client.
        Returns:
            OAuthClientInformationFull | None: Value produced by get_client."""
        record = await self._repository.get_client(client_id)
        if record is None:
            return None
        payload = dict(record.metadata)
        payload.update(
            {
                "client_id": record.client_id,
                "client_secret": (
                    None
                    if record.client_secret_ciphertext is None
                    else self._secret_cipher.decrypt(record.client_secret_ciphertext)
                ),
                "client_id_issued_at": record.issued_at,
                "client_secret_expires_at": record.secret_expires_at,
            }
        )
        return OAuthClientInformationFull.model_validate(payload)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Persist one SDK-validated dynamic client registration.

        Args:
            client_info: Value supplied to register_client."""
        client_id = client_info.client_id
        if client_id is None:
            raise ValueError("OAuth client registration requires client_id")
        metadata = _JSON_OBJECT_ADAPTER.validate_python(
            client_info.model_dump(
                mode="json",
                exclude={
                    "client_id",
                    "client_secret",
                    "client_id_issued_at",
                    "client_secret_expires_at",
                },
            )
        )
        encrypted_secret = (
            None
            if client_info.client_secret is None
            else self._secret_cipher.encrypt(client_info.client_secret)
        )
        await self._repository.save_client(
            client_id=client_id,
            client_secret_ciphertext=encrypted_secret,
            metadata=metadata,
            issued_at=client_info.client_id_issued_at or _now(),
            secret_expires_at=client_info.client_secret_expires_at,
        )

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Create a pending local approval request and return its browser URL.

        Args:
            client: Value supplied to authorize.
            params: Value supplied to authorize.
        Returns:
            str: Value produced by authorize."""
        client_id = client.client_id
        if client_id is None:
            raise AuthorizeError("unauthorized_client", "OAuth client is missing id")
        resource = params.resource or self._settings.resource_url
        if resource != self._settings.resource_url:
            raise AuthorizeError(
                "invalid_request",
                "OAuth resource does not match the Alexandria MCP endpoint",
            )
        scopes = tuple(params.scopes or self._settings.default_scopes)
        if not set(self._settings.required_scopes).issubset(scopes):
            raise AuthorizeError(
                "invalid_scope",
                "OAuth request is missing required Alexandria MCP scopes",
            )
        now = _now()
        request_id = _opaque_value()
        await self._repository.create_authorization_request(
            LocalOAuthAuthorizationRequestRecord(
                request_id=request_id,
                client_id=client_id,
                client_name=client.client_name,
                state=params.state,
                scopes=scopes,
                code_challenge=params.code_challenge,
                redirect_uri=str(params.redirect_uri),
                redirect_uri_provided_explicitly=(
                    params.redirect_uri_provided_explicitly
                ),
                resource=resource,
                expires_at=now + self._settings.approval_ttl_seconds,
                approval_attempts=0,
                consumed_at=None,
            )
        )
        query = urlencode({"request_id": request_id})
        return f"{self._settings.issuer_url.rstrip('/')}/approve?{query}"

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        """Load one unconsumed authorization code for SDK PKCE validation.

        Args:
            client: Value supplied to load_authorization_code.
            authorization_code: Value supplied to load_authorization_code.
        Returns:
            AuthorizationCode | None: Value produced by load_authorization_code."""
        record = await self._repository.get_authorization_code(
            raw_code=authorization_code,
            code_hash=_hash_opaque(authorization_code),
            now=_now(),
        )
        if record is None or record.client_id != client.client_id:
            return None
        return AuthorizationCode(
            code=record.code,
            scopes=list(record.scopes),
            expires_at=record.expires_at,
            client_id=record.client_id,
            code_challenge=record.code_challenge,
            redirect_uri=record.redirect_uri,
            redirect_uri_provided_explicitly=(record.redirect_uri_provided_explicitly),
            resource=record.resource,
        )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        """Consume one code and atomically issue an access/refresh pair.

        Args:
            client: Value supplied to exchange_authorization_code.
            authorization_code: Value supplied to exchange_authorization_code.
        Returns:
            OAuthToken: Value produced by exchange_authorization_code."""
        if authorization_code.client_id != client.client_id:
            raise TokenError("invalid_grant", "authorization code client mismatch")
        access_token = _opaque_value()
        refresh_token = _opaque_value()
        now = _now()
        exchanged = await self._repository.exchange_authorization_code(
            code_hash=_hash_opaque(authorization_code.code),
            access_token_hash=_hash_opaque(access_token),
            refresh_token_hash=_hash_opaque(refresh_token),
            family_id=secrets.token_hex(32),
            access_expires_at=now + self._settings.access_token_ttl_seconds,
            refresh_expires_at=now + self._settings.refresh_token_ttl_seconds,
            now=now,
        )
        if exchanged is None:
            raise TokenError("invalid_grant", "authorization code is unavailable")
        return OAuthToken(
            access_token=access_token,
            expires_in=self._settings.access_token_ttl_seconds,
            scope=" ".join(exchanged.scopes),
            refresh_token=refresh_token,
        )

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        """Load one active refresh token by opaque value.

        Args:
            client: Value supplied to load_refresh_token.
            refresh_token: Value supplied to load_refresh_token.
        Returns:
            RefreshToken | None: Value produced by load_refresh_token."""
        record = await self._repository.get_token(
            raw_token=refresh_token,
            token_hash=_hash_opaque(refresh_token),
            token_kind=LocalOAuthTokenKind.REFRESH,
            now=_now(),
        )
        if record is None or record.client_id != client.client_id:
            return None
        return RefreshToken(
            token=record.token,
            client_id=record.client_id,
            scopes=list(record.scopes),
            expires_at=record.expires_at,
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Rotate one refresh-token family and issue a replacement pair.

        Args:
            client: Value supplied to exchange_refresh_token.
            refresh_token: Value supplied to exchange_refresh_token.
            scopes: Value supplied to exchange_refresh_token.
        Returns:
            OAuthToken: Value produced by exchange_refresh_token."""
        if refresh_token.client_id != client.client_id:
            raise TokenError("invalid_grant", "refresh token client mismatch")
        next_access = _opaque_value()
        next_refresh = _opaque_value()
        now = _now()
        rotated = await self._repository.rotate_refresh_token(
            old_refresh_hash=_hash_opaque(refresh_token.token),
            access_token_hash=_hash_opaque(next_access),
            refresh_token_hash=_hash_opaque(next_refresh),
            scopes=tuple(scopes),
            access_expires_at=now + self._settings.access_token_ttl_seconds,
            refresh_expires_at=now + self._settings.refresh_token_ttl_seconds,
            now=now,
        )
        if rotated is None:
            raise TokenError("invalid_grant", "refresh token is unavailable")
        return OAuthToken(
            access_token=next_access,
            expires_in=self._settings.access_token_ttl_seconds,
            scope=" ".join(rotated.scopes),
            refresh_token=next_refresh,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Verify one opaque bearer token against the durable token store.

        Args:
            token: Value supplied to load_access_token.
        Returns:
            AccessToken | None: Value produced by load_access_token."""
        record = await self._repository.get_token(
            raw_token=token,
            token_hash=_hash_opaque(token),
            token_kind=LocalOAuthTokenKind.ACCESS,
            now=_now(),
        )
        if record is None:
            return None
        return AccessToken(
            token=record.token,
            client_id=record.client_id,
            scopes=list(record.scopes),
            expires_at=record.expires_at,
            resource=record.resource,
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Revoke the complete access/refresh family for one opaque token.

        Args:
            token: Value supplied to revoke_token."""
        await self._repository.revoke_token_family(
            _hash_opaque(token.token),
            _now(),
        )

    async def pending_authorization(
        self,
        request_id: str,
    ) -> LocalOAuthAuthorizationRequestRecord:
        """Return one valid approval request for the local browser screen.

        Args:
            request_id: Value supplied to pending_authorization.
        Returns:
            LocalOAuthAuthorizationRequestRecord: Value produced by pending_authorization."""
        record = await self._repository.get_authorization_request(request_id)
        now = _now()
        if record is None or record.consumed_at is not None or record.expires_at <= now:
            raise LocalOAuthApprovalError(
                HTTPStatus.BAD_REQUEST,
                "OAuth approval request is invalid or expired",
            )
        if record.approval_attempts >= self._settings.max_approval_attempts:
            raise LocalOAuthApprovalError(
                HTTPStatus.TOO_MANY_REQUESTS,
                "OAuth approval request is locked",
            )
        return record

    async def create_pairing_code(self) -> LocalOAuthPairingCode:
        """Create one short-lived code without exposing OAuth bearer tokens.

        Returns:
            Newly generated single-use pairing code and expiry epoch.
        """
        code = _pairing_code()
        now = _now()
        expires_at = now + self._settings.pairing_code_ttl_seconds
        await self._repository.create_pairing_code(
            code_hash=_hash_opaque(code),
            expires_at=expires_at,
            now=now,
        )
        return LocalOAuthPairingCode(code=code, expires_at=expires_at)

    async def approve_authorization(
        self,
        *,
        request_id: str,
        approval_code: str,
    ) -> str:
        """Approve one request with a single-use code or bootstrap operator key.

        Args:
            request_id: Value supplied to approve_authorization.
            approval_code: One-time pairing code or bootstrap operator key.
        Returns:
            str: Value produced by approve_authorization."""
        record = await self.pending_authorization(request_id)
        pairing_code_hash = self._pairing_code_hash(approval_code)
        code = _opaque_value()
        now = _now()
        issued = await self._repository.approve_authorization_request(
            request_id=request_id,
            code=code,
            code_hash=_hash_opaque(code),
            code_expires_at=now + self._settings.authorization_code_ttl_seconds,
            now=now,
            pairing_code_hash=pairing_code_hash,
        )
        if issued is None:
            await self._raise_failed_approval(request_id)
        return construct_redirect_uri(
            record.redirect_uri,
            code=code,
            state=record.state,
        )

    async def deny_authorization(
        self,
        *,
        request_id: str,
        approval_code: str,
    ) -> str:
        """Deny one request with a single-use code or bootstrap operator key.

        Args:
            request_id: Value supplied to deny_authorization.
            approval_code: One-time pairing code or bootstrap operator key.
        Returns:
            str: Value produced by deny_authorization."""
        record = await self.pending_authorization(request_id)
        denied = await self._repository.deny_authorization_request(
            request_id,
            _now(),
            pairing_code_hash=self._pairing_code_hash(approval_code),
        )
        if not denied:
            await self._raise_failed_approval(request_id)
        return construct_redirect_uri(
            record.redirect_uri,
            error="access_denied",
            error_description="Local operator denied MCP access",
            state=record.state,
        )

    def _pairing_code_hash(self, approval_code: str) -> str | None:
        if hmac.compare_digest(
            approval_code.encode("utf-8"),
            self._settings.approval_key.encode("utf-8"),
        ):
            return None
        return _hash_opaque(_normalize_pairing_code(approval_code))

    async def _raise_failed_approval(self, request_id: str) -> None:
        attempts = await self._repository.record_failed_approval(request_id, _now())
        if attempts == 0:
            raise LocalOAuthApprovalError(
                HTTPStatus.BAD_REQUEST,
                "OAuth approval request is no longer available",
            )
        if attempts >= self._settings.max_approval_attempts:
            raise LocalOAuthApprovalError(
                HTTPStatus.TOO_MANY_REQUESTS,
                "OAuth approval request is locked",
            )
        raise LocalOAuthApprovalError(
            HTTPStatus.FORBIDDEN,
            "OAuth pairing code is invalid",
        )


def _opaque_value() -> str:
    return secrets.token_urlsafe(32)


def _pairing_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    compact = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{compact[:4]}-{compact[4:]}"


def _normalize_pairing_code(value: str) -> str:
    compact = "".join(character for character in value.upper() if character.isalnum())
    if len(compact) != 8:
        return compact
    return f"{compact[:4]}-{compact[4:]}"


def _hash_opaque(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> int:
    return int(time.time())
