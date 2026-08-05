"""Exact path and metadata-backed canonical report identity resolution."""

from __future__ import annotations

from datetime import date as calendar_date

from app.obsidian.application.notes.obsidian_canonical_note_path import (
    canonical_managed_note_path,
)
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianVaultInventoryRequest,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianCanonicalIdentityResult,
    ObsidianExactPathStatus,
    ObsidianNote,
)
from app.obsidian.infrastructure.markdown.paths import safe_filename
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.shared.exceptions.obsidian_exceptions import (
    ObsidianNotFoundError,
    ObsidianValidationError,
)


class ObsidianCanonicalIdentityService:
    """Resolve exact paths and report aliases without domain-specific hardcoding."""

    def __init__(
        self,
        *,
        obsidian_service: ObsidianService,
        vault_config_store: ObsidianVaultConfigStore,
    ) -> None:
        self._obsidian_service = obsidian_service
        self._vault_config_store = vault_config_store

    async def check_path(self, path: str) -> ObsidianExactPathStatus:
        """Return exact managed-path existence without fuzzy search fallback.

        Args:
            path: Value supplied to check_path.

        Returns:
            Result produced by check_path.
        """
        canonical_path = self._canonical_path(path)
        try:
            note = await self._obsidian_service.read_note_by_path(canonical_path)
        except ObsidianNotFoundError:
            return ObsidianExactPathStatus(
                exists=False,
                relative_path=canonical_path,
            )
        return ObsidianExactPathStatus(
            exists=True,
            relative_path=canonical_path,
            note_id=note.note_id,
            index_status=note.index_status,
        )

    async def resolve(
        self,
        *,
        project: str,
        report: str,
        date: str,
        entity: str,
        edition: str | None = None,
    ) -> ObsidianCanonicalIdentityResult:
        """Resolve one logical report identity using canonical metadata and aliases.

        Args:
            project: Value supplied to resolve.
            report: Value supplied to resolve.
            date: Value supplied to resolve.
            entity: Value supplied to resolve.
            edition: Value supplied to resolve.

        Returns:
            Result produced by resolve.
        """
        try:
            parsed_date = calendar_date.fromisoformat(date)
        except ValueError as exc:
            raise ObsidianValidationError(
                "date must be a valid ISO calendar date"
            ) from exc
        candidates = await self._obsidian_service.inventory_vault(
            ObsidianVaultInventoryRequest()
        )
        matches: list[tuple[ObsidianNote, str, tuple[str, ...]]] = []
        for candidate in candidates:
            try:
                note = await self._obsidian_service.read_note_by_path(
                    candidate.relative_path
                )
            except ObsidianNotFoundError:
                continue
            family = _text(note.frontmatter.get("report_family")) or _text(
                note.frontmatter.get("report")
            )
            aliases = _aliases(note)
            if not family or not _identity_matches(
                note,
                project=project,
                family=family,
                requested_report=report,
                date=date,
                entity=entity,
                edition=edition,
                aliases=aliases,
            ):
                continue
            matches.append((note, family, aliases))

        if len(matches) == 1:
            note, family, aliases = matches[0]
            return ObsidianCanonicalIdentityResult(
                canonical_report_family=family,
                canonical_entity=_text(note.frontmatter.get("entity")) or entity,
                canonical_path=note.relative_path,
                existing_note_id=note.note_id,
                aliases=aliases,
                resolution="EXISTING_CANONICAL_FAMILY",
            )
        generated_path = self._generated_path(
            project=project,
            report=report,
            parsed_date=parsed_date,
            entity=entity,
            edition=edition,
        )
        if len(matches) > 1:
            return ObsidianCanonicalIdentityResult(
                canonical_report_family=report,
                canonical_entity=entity,
                canonical_path=generated_path,
                existing_note_id=None,
                aliases=(),
                resolution="AMBIGUOUS_CANONICAL_IDENTITY",
                candidate_paths=tuple(item[0].relative_path for item in matches),
            )
        return ObsidianCanonicalIdentityResult(
            canonical_report_family=report,
            canonical_entity=entity,
            canonical_path=generated_path,
            existing_note_id=None,
            aliases=(),
            resolution="NEW_CANONICAL_IDENTITY",
        )

    def _canonical_path(self, path: str) -> str:
        return canonical_managed_note_path(
            path,
            alexandria_root=self._vault_config_store.current().alexandria_root,
        )

    def _generated_path(
        self,
        *,
        project: str,
        report: str,
        parsed_date: calendar_date,
        entity: str,
        edition: str | None,
    ) -> str:
        title_parts = [project, report, entity, parsed_date.isoformat()]
        if edition:
            title_parts.append(edition)
        relative = "/".join(
            [
                "Contexts",
                "Projects",
                project,
                "Daily",
                f"{parsed_date.year:04d}",
                f"{parsed_date.month:02d}",
                report,
                entity,
                safe_filename(" ".join(title_parts)),
            ]
        )
        return self._canonical_path(relative)


def _identity_matches(
    note: ObsidianNote,
    *,
    project: str,
    family: str,
    requested_report: str,
    date: str,
    entity: str,
    edition: str | None,
    aliases: tuple[str, ...],
) -> bool:
    note_project = note.project or _text(note.frontmatter.get("project"))
    note_date = _text(note.frontmatter.get("date"))
    note_entity = _text(note.frontmatter.get("entity"))
    note_edition = _text(note.frontmatter.get("edition"))
    report_names = {_normalized(family), *(_normalized(alias) for alias in aliases)}
    return (
        _normalized(note_project) == _normalized(project)
        and note_date == date
        and _normalized(note_entity) == _normalized(entity)
        and _normalized(requested_report) in report_names
        and (edition is None or _normalized(note_edition) == _normalized(edition))
    )


def _aliases(note: ObsidianNote) -> tuple[str, ...]:
    values: list[str] = []
    for field in ("aliases", "report_aliases"):
        value = note.frontmatter.get(field)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    return tuple(dict.fromkeys(values))


# Broad type justified: frontmatter lookup values may have heterogeneous runtime types.
def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _normalized(value: str | None) -> str:
    return "" if value is None else " ".join(value.casefold().split())
