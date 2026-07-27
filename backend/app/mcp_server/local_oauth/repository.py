"""Transactional repository for local MCP OAuth state."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.mcp_server.local_oauth.contracts import (
    LocalOAuthAuthorizationCodeRecord,
    LocalOAuthAuthorizationRequestRecord,
    LocalOAuthClientRecord,
    LocalOAuthTokenKind,
    LocalOAuthTokenRecord,
)
from app.mcp_server.local_oauth.orm import (
    McpOAuthAuthorizationCodeORM,
    McpOAuthAuthorizationRequestORM,
    McpOAuthClientORM,
    McpOAuthPairingCodeORM,
    McpOAuthTokenORM,
)
from app.shared.types.extra_types import JSONObject, JSONValue


class LocalMcpOAuthRepository:
    """Persist one OAuth transaction aggregate with atomic consume/rotation steps.

    The public method count is intentionally above the normal review threshold because
    client registration, authorization codes, and token families must share one
    database transaction boundary to prevent replay and partial token issuance.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Create the OAuth repository.

        Args:
            session_factory: Async SQLAlchemy session factory.
        """
        self._session_factory = session_factory

    async def save_client(
        self,
        *,
        client_id: str,
        client_secret_ciphertext: str | None,
        metadata: JSONObject,
        issued_at: int,
        secret_expires_at: int | None,
    ) -> None:
        """Persist one dynamic OAuth client registration.

        Args:
            client_id: Value supplied to save_client.
            client_secret_ciphertext: Value supplied to save_client.
            metadata: Value supplied to save_client.
            issued_at: Value supplied to save_client.
            secret_expires_at: Value supplied to save_client."""
        async with self._session_factory() as session, session.begin():
            session.add(
                McpOAuthClientORM(
                    client_id=client_id,
                    client_secret_ciphertext=client_secret_ciphertext,
                    client_metadata=metadata,
                    issued_at=issued_at,
                    secret_expires_at=secret_expires_at,
                )
            )

    async def get_client(self, client_id: str) -> LocalOAuthClientRecord | None:
        """Load one dynamic OAuth client registration.

        Args:
            client_id: Value supplied to get_client.
        Returns:
            LocalOAuthClientRecord | None: Value produced by get_client."""
        async with self._session_factory() as session:
            row = await session.get(McpOAuthClientORM, client_id)
        if row is None:
            return None
        return LocalOAuthClientRecord(
            client_id=row.client_id,
            client_secret_ciphertext=row.client_secret_ciphertext,
            metadata=_frozen_mapping(row.client_metadata),
            issued_at=row.issued_at,
            secret_expires_at=row.secret_expires_at,
        )

    async def create_authorization_request(
        self,
        record: LocalOAuthAuthorizationRequestRecord,
    ) -> None:
        """Persist one pending operator approval request.

        Args:
            record: Value supplied to create_authorization_request."""
        async with self._session_factory() as session, session.begin():
            session.add(
                McpOAuthAuthorizationRequestORM(
                    request_id=record.request_id,
                    client_id=record.client_id,
                    client_name=record.client_name,
                    state=record.state,
                    scopes=list(record.scopes),
                    code_challenge=record.code_challenge,
                    redirect_uri=record.redirect_uri,
                    redirect_uri_provided_explicitly=(
                        record.redirect_uri_provided_explicitly
                    ),
                    resource=record.resource,
                    expires_at=record.expires_at,
                    approval_attempts=record.approval_attempts,
                    consumed_at=record.consumed_at,
                )
            )

    async def get_authorization_request(
        self,
        request_id: str,
    ) -> LocalOAuthAuthorizationRequestRecord | None:
        """Load one pending operator approval request.

        Args:
            request_id: Value supplied to get_authorization_request.
        Returns:
            LocalOAuthAuthorizationRequestRecord | None: Value produced by get_authorization_request."""
        async with self._session_factory() as session:
            row = await session.get(McpOAuthAuthorizationRequestORM, request_id)
        return None if row is None else _authorization_request_record(row)

    async def record_failed_approval(self, request_id: str, now: int) -> int:
        """Increment a pending request's failed approval attempts.

        Args:
            request_id: Value supplied to record_failed_approval.
            now: Value supplied to record_failed_approval.
        Returns:
            int: Value produced by record_failed_approval."""
        async with self._session_factory() as session, session.begin():
            row = await session.get(McpOAuthAuthorizationRequestORM, request_id)
            if row is None or row.consumed_at is not None or row.expires_at <= now:
                return 0
            row.approval_attempts += 1
            return row.approval_attempts

    async def create_pairing_code(
        self,
        *,
        code_hash: str,
        expires_at: int,
        now: int,
    ) -> None:
        """Replace prior active pairing codes with one new hashed code.

        Args:
            code_hash: SHA-256 lookup value for the code.
            expires_at: Pairing-code expiry epoch.
            now: Current epoch.
        """
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(McpOAuthPairingCodeORM)
                .where(McpOAuthPairingCodeORM.consumed_at.is_(None))
                .values(consumed_at=now)
            )
            session.add(
                McpOAuthPairingCodeORM(
                    code_hash=code_hash,
                    expires_at=expires_at,
                    consumed_at=None,
                    created_at=now,
                )
            )

    async def approve_authorization_request(
        self,
        *,
        request_id: str,
        code: str,
        code_hash: str,
        code_expires_at: int,
        now: int,
        pairing_code_hash: str | None = None,
    ) -> LocalOAuthAuthorizationCodeRecord | None:
        """Consume one approval request and atomically create its code.

        Args:
            request_id: Value supplied to approve_authorization_request.
            code: Value supplied to approve_authorization_request.
            code_hash: Value supplied to approve_authorization_request.
            code_expires_at: Value supplied to approve_authorization_request.
            now: Value supplied to approve_authorization_request.
        Returns:
            LocalOAuthAuthorizationCodeRecord | None: Value produced by approve_authorization_request."""
        async with self._session_factory() as session, session.begin():
            request_row = await session.get(
                McpOAuthAuthorizationRequestORM,
                request_id,
            )
            if (
                request_row is None
                or request_row.consumed_at is not None
                or request_row.expires_at <= now
            ):
                return None
            if pairing_code_hash is not None:
                pairing_row = await session.get(
                    McpOAuthPairingCodeORM,
                    pairing_code_hash,
                )
                if (
                    pairing_row is None
                    or pairing_row.consumed_at is not None
                    or pairing_row.expires_at <= now
                ):
                    return None
                pairing_row.consumed_at = now
            request_row.consumed_at = now
            session.add(
                McpOAuthAuthorizationCodeORM(
                    code_hash=code_hash,
                    client_id=request_row.client_id,
                    scopes=list(request_row.scopes),
                    code_challenge=request_row.code_challenge,
                    redirect_uri=request_row.redirect_uri,
                    redirect_uri_provided_explicitly=(
                        request_row.redirect_uri_provided_explicitly
                    ),
                    resource=request_row.resource,
                    expires_at=code_expires_at,
                    consumed_at=None,
                )
            )
            return LocalOAuthAuthorizationCodeRecord(
                code=code,
                client_id=request_row.client_id,
                scopes=tuple(request_row.scopes),
                code_challenge=request_row.code_challenge,
                redirect_uri=request_row.redirect_uri,
                redirect_uri_provided_explicitly=(
                    request_row.redirect_uri_provided_explicitly
                ),
                resource=request_row.resource,
                expires_at=code_expires_at,
            )

    async def deny_authorization_request(
        self,
        request_id: str,
        now: int,
        *,
        pairing_code_hash: str | None = None,
    ) -> bool:
        """Consume one pending request without issuing a code.

        Args:
            request_id: Value supplied to deny_authorization_request.
            now: Value supplied to deny_authorization_request.
        Returns:
            bool: Value produced by deny_authorization_request."""
        async with self._session_factory() as session, session.begin():
            row = await session.get(McpOAuthAuthorizationRequestORM, request_id)
            if row is None or row.consumed_at is not None or row.expires_at <= now:
                return False
            if pairing_code_hash is not None:
                pairing_row = await session.get(
                    McpOAuthPairingCodeORM,
                    pairing_code_hash,
                )
                if (
                    pairing_row is None
                    or pairing_row.consumed_at is not None
                    or pairing_row.expires_at <= now
                ):
                    return False
                pairing_row.consumed_at = now
            row.consumed_at = now
            return True

    async def get_authorization_code(
        self,
        *,
        raw_code: str,
        code_hash: str,
        now: int,
    ) -> LocalOAuthAuthorizationCodeRecord | None:
        """Load one active authorization code by its hashed lookup key.

        Args:
            raw_code: Value supplied to get_authorization_code.
            code_hash: Value supplied to get_authorization_code.
            now: Value supplied to get_authorization_code.
        Returns:
            LocalOAuthAuthorizationCodeRecord | None: Value produced by get_authorization_code."""
        async with self._session_factory() as session:
            row = await session.get(McpOAuthAuthorizationCodeORM, code_hash)
        if row is None or row.consumed_at is not None or row.expires_at <= now:
            return None
        return LocalOAuthAuthorizationCodeRecord(
            code=raw_code,
            client_id=row.client_id,
            scopes=tuple(row.scopes),
            code_challenge=row.code_challenge,
            redirect_uri=row.redirect_uri,
            redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
            resource=row.resource,
            expires_at=row.expires_at,
        )

    async def exchange_authorization_code(
        self,
        *,
        code_hash: str,
        access_token_hash: str,
        refresh_token_hash: str,
        family_id: str,
        access_expires_at: int,
        refresh_expires_at: int,
        now: int,
    ) -> LocalOAuthAuthorizationCodeRecord | None:
        """Consume a code and atomically persist its access/refresh token pair.

        Args:
            code_hash: Value supplied to exchange_authorization_code.
            access_token_hash: Value supplied to exchange_authorization_code.
            refresh_token_hash: Value supplied to exchange_authorization_code.
            family_id: Value supplied to exchange_authorization_code.
            access_expires_at: Value supplied to exchange_authorization_code.
            refresh_expires_at: Value supplied to exchange_authorization_code.
            now: Value supplied to exchange_authorization_code.
        Returns:
            LocalOAuthAuthorizationCodeRecord | None: Value produced by exchange_authorization_code."""
        async with self._session_factory() as session, session.begin():
            row = await session.get(McpOAuthAuthorizationCodeORM, code_hash)
            if row is None or row.consumed_at is not None or row.expires_at <= now:
                return None
            row.consumed_at = now
            _add_token_pair(
                session,
                client_id=row.client_id,
                scopes=row.scopes,
                resource=row.resource,
                family_id=family_id,
                access_token_hash=access_token_hash,
                refresh_token_hash=refresh_token_hash,
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                now=now,
            )
            return LocalOAuthAuthorizationCodeRecord(
                code="",
                client_id=row.client_id,
                scopes=tuple(row.scopes),
                code_challenge=row.code_challenge,
                redirect_uri=row.redirect_uri,
                redirect_uri_provided_explicitly=(row.redirect_uri_provided_explicitly),
                resource=row.resource,
                expires_at=row.expires_at,
            )

    async def get_token(
        self,
        *,
        raw_token: str,
        token_hash: str,
        token_kind: LocalOAuthTokenKind,
        now: int,
    ) -> LocalOAuthTokenRecord | None:
        """Load one active opaque token by its hashed lookup key.

        Args:
            raw_token: Value supplied to get_token.
            token_hash: Value supplied to get_token.
            token_kind: Value supplied to get_token.
            now: Value supplied to get_token.
        Returns:
            LocalOAuthTokenRecord | None: Value produced by get_token."""
        async with self._session_factory() as session:
            row = await session.get(McpOAuthTokenORM, token_hash)
        if (
            row is None
            or row.token_kind != token_kind.value
            or row.revoked_at is not None
            or row.expires_at <= now
        ):
            return None
        return LocalOAuthTokenRecord(
            token=raw_token,
            token_kind=token_kind,
            family_id=row.family_id,
            client_id=row.client_id,
            scopes=tuple(row.scopes),
            resource=row.resource,
            expires_at=row.expires_at,
        )

    async def rotate_refresh_token(
        self,
        *,
        old_refresh_hash: str,
        access_token_hash: str,
        refresh_token_hash: str,
        scopes: tuple[str, ...],
        access_expires_at: int,
        refresh_expires_at: int,
        now: int,
    ) -> LocalOAuthTokenRecord | None:
        """Revoke one token family and atomically issue its rotated pair.

        Args:
            old_refresh_hash: Value supplied to rotate_refresh_token.
            access_token_hash: Value supplied to rotate_refresh_token.
            refresh_token_hash: Value supplied to rotate_refresh_token.
            scopes: Value supplied to rotate_refresh_token.
            access_expires_at: Value supplied to rotate_refresh_token.
            refresh_expires_at: Value supplied to rotate_refresh_token.
            now: Value supplied to rotate_refresh_token.
        Returns:
            LocalOAuthTokenRecord | None: Value produced by rotate_refresh_token."""
        async with self._session_factory() as session, session.begin():
            old_row = await session.get(McpOAuthTokenORM, old_refresh_hash)
            if (
                old_row is None
                or old_row.token_kind != LocalOAuthTokenKind.REFRESH.value
                or old_row.revoked_at is not None
                or old_row.expires_at <= now
                or not set(scopes).issubset(set(old_row.scopes))
            ):
                return None
            await session.execute(
                update(McpOAuthTokenORM)
                .where(
                    McpOAuthTokenORM.family_id == old_row.family_id,
                    McpOAuthTokenORM.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            _add_token_pair(
                session,
                client_id=old_row.client_id,
                scopes=list(scopes),
                resource=old_row.resource,
                family_id=old_row.family_id,
                access_token_hash=access_token_hash,
                refresh_token_hash=refresh_token_hash,
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                now=now,
            )
            return LocalOAuthTokenRecord(
                token="",
                token_kind=LocalOAuthTokenKind.REFRESH,
                family_id=old_row.family_id,
                client_id=old_row.client_id,
                scopes=scopes,
                resource=old_row.resource,
                expires_at=refresh_expires_at,
            )

    async def revoke_token_family(self, token_hash: str, now: int) -> None:
        """Revoke both access and refresh tokens belonging to one family.

        Args:
            token_hash: Value supplied to revoke_token_family.
            now: Value supplied to revoke_token_family."""
        async with self._session_factory() as session, session.begin():
            row = await session.get(McpOAuthTokenORM, token_hash)
            if row is None:
                return
            await session.execute(
                update(McpOAuthTokenORM)
                .where(
                    McpOAuthTokenORM.family_id == row.family_id,
                    McpOAuthTokenORM.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )


def _authorization_request_record(
    row: McpOAuthAuthorizationRequestORM,
) -> LocalOAuthAuthorizationRequestRecord:
    return LocalOAuthAuthorizationRequestRecord(
        request_id=row.request_id,
        client_id=row.client_id,
        client_name=row.client_name,
        state=row.state,
        scopes=tuple(row.scopes),
        code_challenge=row.code_challenge,
        redirect_uri=row.redirect_uri,
        redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
        resource=row.resource,
        expires_at=row.expires_at,
        approval_attempts=row.approval_attempts,
        consumed_at=row.consumed_at,
    )


def _frozen_mapping(value: JSONObject) -> Mapping[str, JSONValue]:
    return MappingProxyType(dict(value))


def _add_token_pair(
    session: AsyncSession,
    *,
    client_id: str,
    scopes: list[str],
    resource: str,
    family_id: str,
    access_token_hash: str,
    refresh_token_hash: str,
    access_expires_at: int,
    refresh_expires_at: int,
    now: int,
) -> None:
    session.add_all(
        (
            McpOAuthTokenORM(
                token_hash=access_token_hash,
                token_kind=LocalOAuthTokenKind.ACCESS.value,
                family_id=family_id,
                client_id=client_id,
                scopes=list(scopes),
                resource=resource,
                expires_at=access_expires_at,
                revoked_at=None,
                created_at=now,
            ),
            McpOAuthTokenORM(
                token_hash=refresh_token_hash,
                token_kind=LocalOAuthTokenKind.REFRESH.value,
                family_id=family_id,
                client_id=client_id,
                scopes=list(scopes),
                resource=resource,
                expires_at=refresh_expires_at,
                revoked_at=None,
                created_at=now,
            ),
        )
    )
