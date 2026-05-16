"""Scan and import external MINIO archive objects into the library catalog."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import cast

from app.archive.domain.contracts.minio_import_contracts import (
    MinioImportCandidate,
    MinioImportResult,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import ProviderType
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.library.application.item_service import ItemService
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.platform.storage.minio_object_content import MinioObjectContentClient
from app.platform.storage.minio_object_listing import (
    DEFAULT_REGION,
    MAX_MINIO_LIST_LIMIT,
    MinioObjectListingClient,
)
from app.platform.storage.minio_types import MinioObject
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.types.types_convert_utils import bool_value, string_value
from minio.error import S3Error
from urllib3.exceptions import HTTPError

MINIO_PROVIDER_TYPE = ProviderType.MINIO
SUPPORTED_IMPORT_SUFFIXES = frozenset(
    {".md", ".markdown", ".txt", ".json", ".xml", ".prompt"}
)
TITLE_FRONTMATTER_PATTERN = re.compile(r"^title:\s*(?P<title>.+)$", re.IGNORECASE)
SUMMARY_FRONTMATTER_PATTERN = re.compile(r"^summary:\s*(?P<summary>.+)$", re.IGNORECASE)
TYPE_FRONTMATTER_PATTERN = re.compile(
    r"^(type|item_type):\s*(?P<value>.+)$", re.IGNORECASE
)
KIND_FRONTMATTER_PATTERN = re.compile(
    r"^(kind|prompt_kind):\s*(?P<value>.+)$", re.IGNORECASE
)
FORMAT_FRONTMATTER_PATTERN = re.compile(
    r"^(format|content_format):\s*(?P<value>.+)$", re.IGNORECASE
)
DOMAIN_FRONTMATTER_PATTERN = re.compile(
    r"^(domain|prompt_domain):\s*(?P<value>.+)$", re.IGNORECASE
)
TASK_FRONTMATTER_PATTERN = re.compile(
    r"^(task_type|prompt_task_type):\s*(?P<value>.+)$", re.IGNORECASE
)
TAG_SPLIT_PATTERN = re.compile(r"[^a-zA-Z0-9가-힣_-]+")


@dataclass(frozen=True, slots=True)
class _MinioProviderConfig:
    endpoint: str
    bucket: str
    prefix: str
    region: str
    access_key: str
    secret_key: str


class MinioArchiveImportUseCase:
    """Build import candidates and persist approved candidates as library items."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        item_service: ItemService,
    ) -> None:
        """Initialize use case dependencies.

        Args:
            provider_repo: Repository for stored librarian providers.
            secret_repo: Repository for provider credentials.
            item_service: Catalog item service used for linked imports.
        """
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.item_service = item_service

    async def scan(self, limit: int) -> list[MinioImportCandidate]:
        """Scan enabled MINIO providers and return inferred import candidates.

        Args:
            limit: Maximum number of candidates to return.

        Returns:
            Library import candidates inferred from supported external objects.
        """
        bounded_limit = max(1, min(limit, MAX_MINIO_LIST_LIMIT))
        listing_client = MinioObjectListingClient()
        content_client = MinioObjectContentClient()
        providers = await self._enabled_minio_providers()
        candidates: list[MinioImportCandidate] = []
        for provider in providers:
            provider_candidates = await self._scan_provider(
                provider=provider,
                listing_client=listing_client,
                content_client=content_client,
                limit=bounded_limit,
            )
            candidates.extend(provider_candidates)
        scanned_candidates = list(_limit(candidates, bounded_limit))
        return scanned_candidates

    async def import_linked(self, limit: int) -> MinioImportResult:
        """Import scanned candidates while keeping originals linked.

        Args:
            limit: Maximum number of candidates to scan and import.

        Returns:
            Count summary and created item identifiers.
        """
        candidates = await self.scan(limit=limit)
        existing_refs = await self._existing_storage_refs()
        imported_ids: list[str] = []
        skipped_count = 0
        for candidate in candidates:
            ref_key = _storage_ref_key(candidate.details)
            if ref_key in existing_refs:
                skipped_count += 1
                continue
            payload = await self.item_service.create_item(
                item_type=candidate.item_type,
                title=candidate.title,
                summary=candidate.summary,
                content=candidate.content_preview
                or f"s3://{candidate.bucket}/{candidate.object_key}",
                category_id=None,
                tags=candidate.tags,
                status=ItemStatus.ACTIVE,
                source_type=SourceType.IMPORTED,
                created_by_type=CreatedByType.LIBRARIAN,
                created_by_name="Hermes Importer",
                details=candidate.details,
            )
            imported_ids.append(cast(str, payload["id"]))
            existing_refs.add(ref_key)
        result = MinioImportResult(
            imported_count=len(imported_ids),
            skipped_count=skipped_count,
            item_ids=imported_ids,
        )
        return result

    async def _scan_provider(
        self,
        provider: LibrarianProvider,
        listing_client: MinioObjectListingClient,
        content_client: MinioObjectContentClient,
        limit: int,
    ) -> list[MinioImportCandidate]:
        provider_config = await self._minio_provider_config(provider)
        if provider_config is None:
            return []
        try:
            objects = await asyncio.to_thread(
                listing_client.list_objects,
                endpoint=provider_config.endpoint,
                bucket=provider_config.bucket,
                prefix=provider_config.prefix,
                region=provider_config.region,
                access_key=provider_config.access_key,
                secret_key=provider_config.secret_key,
                limit=limit,
            )
        except (OSError, ValueError, S3Error, HTTPError):
            return []
        candidates: list[MinioImportCandidate] = []
        for item in _supported_objects(objects):
            content = await self._read_content(
                content_client=content_client,
                provider_config=provider_config,
                item=item,
            )
            candidate = _candidate_from_object(
                provider=provider,
                provider_config=provider_config,
                item=item,
                content=content,
            )
            candidates.append(candidate)
        return candidates

    async def _read_content(
        self,
        content_client: MinioObjectContentClient,
        provider_config: _MinioProviderConfig,
        item: MinioObject,
    ) -> str:
        try:
            content = await asyncio.to_thread(
                content_client.read_text_object,
                endpoint=provider_config.endpoint,
                bucket=provider_config.bucket,
                object_key=item.key,
                region=provider_config.region,
                access_key=provider_config.access_key,
                secret_key=provider_config.secret_key,
            )
        except (OSError, ValueError, S3Error, HTTPError):
            return ""
        return content

    async def _enabled_minio_providers(self) -> list[LibrarianProvider]:
        providers = [
            provider
            for provider in await self.provider_repo.list_all()
            if provider.enabled and provider.provider_type == MINIO_PROVIDER_TYPE
        ]
        return providers

    async def _minio_provider_config(
        self,
        provider: LibrarianProvider,
    ) -> _MinioProviderConfig | None:
        endpoint = string_value(provider.config.get("endpoint")).strip()
        bucket = string_value(provider.config.get("bucket")).strip()
        prefix = string_value(provider.config.get("prefix")).strip()
        region = (
            string_value(provider.config.get("region"), default=DEFAULT_REGION).strip()
            or DEFAULT_REGION
        )
        if bool_value(provider.config.get("use_ssl")) and endpoint.startswith(
            "http://"
        ):
            endpoint = "https://" + endpoint.removeprefix("http://")
        secret = await self.secret_repo.resolve(provider.id, "api_key")
        secret_pair = _split_minio_secret(secret or "")
        if not endpoint or not bucket or secret_pair is None:
            return None
        access_key, secret_key = secret_pair
        provider_config = _MinioProviderConfig(
            endpoint=endpoint,
            bucket=bucket,
            prefix=prefix,
            region=region,
            access_key=access_key,
            secret_key=secret_key,
        )
        return provider_config

    async def _existing_storage_refs(self) -> set[str]:
        payloads, _ = await self.item_service.list_items(limit=1000)
        refs = {
            _storage_ref_key(cast(JSONObject, payload.get("details", {})))
            for payload in payloads
        }
        refs.discard("")
        return refs


def _candidate_from_object(
    provider: LibrarianProvider,
    provider_config: _MinioProviderConfig,
    item: MinioObject,
    content: str,
) -> MinioImportCandidate:
    title = _frontmatter_value(content, TITLE_FRONTMATTER_PATTERN) or _object_title(
        item.key
    )
    summary = _frontmatter_value(
        content, SUMMARY_FRONTMATTER_PATTERN
    ) or _summary_from_content(content)
    item_type, confidence = _classify_item(item.key, content)
    preview = _content_preview(content) or f"s3://{provider_config.bucket}/{item.key}"
    tags = _tags_from_path(item.key, provider_config.bucket)
    prompt_details = _prompt_details_from_object(item.key, content, item_type)
    details: JSONObject = {
        "storage": {
            "type": "OBJECT_STORAGE",
            "provider_type": "MINIO",
            "provider_id": provider.id,
            "endpoint": provider_config.endpoint,
            "bucket": provider_config.bucket,
            "object_key": item.key,
            "etag": item.etag,
            "size": item.size,
        },
        "import": {
            "mode": "LINKED",
            "confidence": confidence,
            "needs_review": confidence < 0.75,
            "content_hash": _content_hash(content),
        },
    }
    if prompt_details is not None:
        details.update(prompt_details)
    candidate = MinioImportCandidate(
        id=f"minio-import:{provider.id}:{hashlib.sha256(item.key.encode()).hexdigest()[:16]}",
        provider_id=provider.id,
        bucket=provider_config.bucket,
        object_key=item.key,
        title=title,
        summary=summary,
        content_preview=preview,
        item_type=item_type,
        tags=tags,
        details=details,
        confidence=confidence,
        needs_review=confidence < 0.75,
    )
    return candidate


def _classify_item(key: str, content: str) -> tuple[ItemType, float]:
    haystack = f"{key}\n{content[:500]}".lower()
    normalized_key = f"/{key.lower()}"
    explicit_type = _frontmatter_value(content, TYPE_FRONTMATTER_PATTERN)
    if explicit_type and explicit_type.strip().upper() == "PROMPT":
        return ItemType.PROMPT, 0.9
    if (
        ".prompt" in key.lower()
        or "/library/prompts/" in normalized_key
        or key.lower().startswith("prompts/")
        or "prompt_kind" in haystack
        or "{{" in haystack
    ):
        return ItemType.PROMPT, 0.82
    if "workflow" in haystack or "checklist" in haystack or "runbook" in haystack:
        return ItemType.WORKFLOW, 0.78
    if "skill" in haystack or "purpose:" in haystack or "required_tools" in haystack:
        return ItemType.SKILL, 0.78
    if "/library/skills/" in normalized_key or key.lower().startswith("skills/"):
        return ItemType.SKILL, 0.72
    return ItemType.KNOWLEDGE, 0.55


def _prompt_details_from_object(
    key: str, content: str, item_type: ItemType
) -> JSONObject | None:
    if item_type is not ItemType.PROMPT:
        return None
    details: JSONObject = {
        "content_format": _prompt_format_from_object(key, content),
        "prompt_kind": _prompt_enum_hint(
            _frontmatter_value(content, KIND_FRONTMATTER_PATTERN),
            default="USER_TEMPLATE",
        ),
        "prompt_domain": _prompt_enum_hint(
            _frontmatter_value(content, DOMAIN_FRONTMATTER_PATTERN),
            default="GENERAL",
        ),
        "prompt_task_type": _prompt_enum_hint(
            _frontmatter_value(content, TASK_FRONTMATTER_PATTERN),
            default="GENERAL_TASK",
        ),
        "input_variables": _prompt_variables_from_content(content),
        "output_format": None,
        "target_actor": None,
        "target_model_family": None,
        "language": None,
        "related_item_ids": [],
        "safety_notes": None,
        "version": "1.0.0",
        "change_summary": "Imported from MINIO",
    }
    return details


def _prompt_format_from_object(key: str, content: str) -> str:
    raw_format = _frontmatter_value(content, FORMAT_FRONTMATTER_PATTERN)
    if raw_format:
        return _prompt_enum_hint(raw_format, default="MARKDOWN")
    suffix = PurePosixPath(key).suffix.lower()
    if suffix == ".json":
        return "JSON"
    if suffix == ".xml":
        return "XML"
    if suffix == ".txt" or suffix == ".prompt":
        return "TEXT"
    return "MARKDOWN"


def _prompt_enum_hint(value: str | None, default: str) -> str:
    if not value:
        return default
    normalized = TAG_SPLIT_PATTERN.sub("_", value.strip().upper()).strip("_")
    return normalized or default


def _prompt_variables_from_content(content: str) -> list[JSONObject]:
    names = sorted(set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", content)))
    variables: list[JSONObject] = [
        {
            "name": name,
            "required": True,
            "description": None,
            "default_value": None,
            "example": None,
            "input_type": "text",
        }
        for name in names
    ]
    return variables


def _frontmatter_value(content: str, pattern: re.Pattern[str]) -> str | None:
    for raw_line in content.splitlines()[:20]:
        match = pattern.match(raw_line.strip())
        if match is not None:
            value = _frontmatter_match_value(match)
            return value or None
    return None


def _frontmatter_match_value(match: re.Match[str]) -> str:
    group_values = match.groupdict()
    raw_value = (
        group_values.get("value")
        or group_values.get("title")
        or group_values.get("summary")
        or match.group(match.lastindex or 1)
    )
    value = raw_value.strip().strip("\"'")
    return value


def _summary_from_content(content: str) -> str:
    for raw_line in content.splitlines():
        line = raw_line.strip().lstrip("# ").strip()
        if not line or line == "---" or ":" in line[:24]:
            continue
        return line[:240]
    return "External archive object ready for library review."


def _content_preview(content: str) -> str:
    preview = content.strip()[:4000]
    return preview


def _content_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode()).hexdigest()
    return f"sha256:{digest}"


def _tags_from_path(key: str, bucket: str) -> list[str]:
    parts = [part for part in PurePosixPath(key).parts[:-1] if part not in {".", ".."}]
    tags = ["external-archive", bucket]
    for part in parts[:4]:
        tag = TAG_SPLIT_PATTERN.sub("-", part.strip().lower()).strip("-")
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _object_title(key: str) -> str:
    stem = PurePosixPath(key.rstrip("/")).stem or key.rstrip("/") or "External archive"
    title = TAG_SPLIT_PATTERN.sub(" ", stem).strip().title()
    return title or "External archive"


def _storage_ref_key(details: JSONObject) -> str:
    storage = details.get("storage")
    if not isinstance(storage, dict):
        return ""
    provider_id = _json_string(storage.get("provider_id"))
    bucket = _json_string(storage.get("bucket"))
    object_key = _json_string(storage.get("object_key"))
    if not provider_id or not bucket or not object_key:
        return ""
    return f"{provider_id}:{bucket}:{object_key}"


def _json_string(value: JSONValue) -> str:
    return value if isinstance(value, str) else ""


def _split_minio_secret(secret: str) -> tuple[str, str] | None:
    access_key, separator, secret_key = secret.partition(":")
    if not separator or not access_key.strip() or not secret_key.strip():
        return None
    secret_pair = access_key.strip(), secret_key.strip()
    return secret_pair


def _supported_objects(objects: Iterable[MinioObject]) -> Iterable[MinioObject]:
    for item in objects:
        suffix = PurePosixPath(item.key).suffix.lower()
        if suffix in SUPPORTED_IMPORT_SUFFIXES:
            yield item


def _limit(
    values: Iterable[MinioImportCandidate], limit: int
) -> Iterable[MinioImportCandidate]:
    for index, value in enumerate(values):
        if index >= limit:
            break
        yield value
