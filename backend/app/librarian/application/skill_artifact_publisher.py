"""Publish acquired skill artifacts into the Obsidian skill library."""

from __future__ import annotations

from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from app.librarian.application.skill_acquisition_service import (
    PublishedSkillArtifact,
    SkillArtifactPublicationError,
)
from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
    SkillAcquisitionEvidenceItem,
)
from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStage,
)
from app.librarian.domain.event_enum.skill_acquisition_enums import (
    ItemStatus,
    RiskLevel,
)
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianSaveNote,
    ObsidianSearchQuery,
)
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.exceptions import LibrarianValidationError
from app.shared.serialization.orjson_codec import dumps_pretty_json
from app.shared.types.extra_types import JSONObject, JSONValue

_REQUIRED_SKILL_SECTIONS: tuple[str, ...] = (
    "## 목적",
    "## 언제 사용해야 하는가",
    "## 언제 사용하지 말아야 하는가",
    "## 입력/사전조건",
    "## 단계별 절차 (Procedure)",
    "## 출력 계약",
    "## 실패 모드와 복구",
    "## 안전·권한·비밀정보 가드레일",
    "## 사용 예시",
    "## Evidence와 claim mapping",
    "## 현재 task에 적용하는 next steps",
    "## 버전/변경 이력",
)


class ObsidianSkillArtifactPublisher:
    """Publish acquired skills as draft Obsidian skill notes."""

    def __init__(self, obsidian_service: ObsidianService) -> None:
        """Create publisher.

        Args:
            obsidian_service: Obsidian application service.
        """
        self._obsidian_service = obsidian_service

    async def publish_skill_artifact(
        self,
        *,
        job: SkillAcquisitionJob,
        artifact: SkillAcquisitionArtifact,
    ) -> PublishedSkillArtifact:
        """Save one skill artifact as a durable draft note.

        Args:
            job: Skill-acquisition job being completed.
            artifact: Structured acquired skill artifact.

        Returns:
            Durable skill handles for job completion.
        """
        _validate_artifact(artifact)
        body = _skill_markdown_body(job=job, artifact=artifact)
        frontmatter = _skill_frontmatter(job=job, artifact=artifact)
        note = await self._obsidian_service.save_note(
            ObsidianSaveNote(
                note_id=_skill_note_id(job.id),
                title=artifact.title,
                body=body,
                alexandria_type=AlexandriaNoteType.SKILL,
                tags=_skill_tags(artifact),
                status="draft",
                project=job.project,
                source="skill_acquisition",
                frontmatter=frontmatter,
            )
        )
        try:
            await self._verify_published_skill(
                note_id=note.note_id,
                title=artifact.title,
                project=job.project,
                expected_body=body,
                expected_frontmatter=frontmatter,
            )
        except LibrarianValidationError as error:
            raise SkillArtifactPublicationError(
                str(error),
                skill_id=note.note_id,
                skill_note_path=note.relative_path,
                stage=SkillAcquisitionJobStage.SKILL_SAVED,
                verification_status="failed",
            ) from error
        handoff = _handoff_payload(
            job=job,
            artifact=artifact,
            note_id=note.note_id,
            note_path=note.relative_path,
        )
        return PublishedSkillArtifact(
            skill_id=note.note_id,
            context_id=None,
            result_summary=f"Saved and verified draft skill note: {note.relative_path}",
            skill_note_path=note.relative_path,
            stage=SkillAcquisitionJobStage.HANDOFF_READY,
            progress_summary=(
                "Searched, saved, reindexed, search-verified, and read-back "
                f"verified draft skill note: {note.relative_path}"
            ),
            reindex_status="succeeded",
            verification_status="verified",
            handoff=handoff,
            repair_hint=None,
        )

    async def _verify_published_skill(
        self,
        *,
        note_id: str,
        title: str,
        project: str | None,
        expected_body: str,
        expected_frontmatter: JSONObject,
    ) -> None:
        saved = await self._obsidian_service.read_note(note_id)
        if saved.note_id != note_id:
            raise LibrarianValidationError("Published skill artifact read-back failed")
        _verify_saved_contract(
            saved_body=saved.body,
            saved_frontmatter=saved.frontmatter,
            expected_body=expected_body,
            expected_frontmatter=expected_frontmatter,
        )
        hits = await self._obsidian_service.search(
            ObsidianSearchQuery(
                query=title,
                limit=10,
                alexandria_type=AlexandriaNoteType.SKILL,
                project=project,
                tags=["skill-acquisition"],
            ),
            refresh=True,
        )
        if not any(hit.note.note_id == note_id for hit in hits):
            raise LibrarianValidationError(
                "Published skill artifact was not found by search"
            )


def _skill_note_id(job_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"alexandria-hermes:skill:{job_id}"))


def _skill_tags(artifact: SkillAcquisitionArtifact) -> list[str]:
    tags = ["skill-acquisition", *artifact.tags]
    deduplicated: list[str] = []
    for tag in tags:
        normalized = tag.strip()
        if normalized and normalized not in deduplicated:
            deduplicated.append(normalized)
    return deduplicated


def _skill_frontmatter(
    *,
    job: SkillAcquisitionJob,
    artifact: SkillAcquisitionArtifact,
) -> JSONObject:
    return {
        "version": artifact.version,
        "purpose": artifact.purpose,
        "when_to_use": [],
        "when_not_to_use": [],
        "required_tools": _clean_items(artifact.required_tools),
        "risk_level": artifact.risk_level.value,
        "created_by": artifact.created_by_name or "librarian",
        "source_job_id": job.id,
        "source_prompt_id": "librarian_operating_prompt_v0_1",
        "evidence_urls": _clean_items(artifact.evidence_urls),
        "evidence_items": _evidence_item_payloads(artifact),
        "source_summary": artifact.source_summary,
        "created_at": job.created_at.isoformat(),
        "reviewed_at": None,
        "supersedes": [],
        "requested_status": artifact.status.value,
        "activate_requested": artifact.activate,
    }


def _skill_markdown_body(
    *,
    job: SkillAcquisitionJob,
    artifact: SkillAcquisitionArtifact,
) -> str:
    usage = artifact.summary or artifact.purpose
    lines = [
        f"# {artifact.title.strip()}",
        "",
        "## 목적",
        artifact.purpose.strip(),
        "",
        "## 언제 사용해야 하는가",
        _bullet_or_none([usage]),
        "",
        "## 언제 사용하지 말아야 하는가",
        _bullet_or_none(
            [
                "필요 도구나 권한이 없으면 적용하지 말고 blocker로 보고한다.",
                "현재 task의 risk tolerance를 초과하면 human review 전 자동 실행하지 않는다.",
            ]
        ),
        "",
        "## 입력/사전조건",
        _input_contract(artifact),
        "",
        "## 단계별 절차 (Procedure)",
        artifact.content.strip(),
        "",
        "## 출력 계약",
        _output_contract(artifact),
        "",
        "## 실패 모드와 복구",
        _bullet_or_none(
            [
                "required tool이 없으면 대체 절차를 추정하지 말고 missing-tool blocker를 반환한다.",
                "절차 검증이 실패하면 생성된 산출물을 사용하지 말고 evidence와 입력 조건을 재확인한다.",
            ]
        ),
        "",
        "## 안전·권한·비밀정보 가드레일",
        _bullet_or_none(
            [
                f"risk_level: {artifact.risk_level.value}",
                "status: draft; human review is required before active promotion",
                "credential, token, private raw log, 개인정보를 skill 본문이나 evidence에 저장하지 않는다.",
            ]
        ),
        "",
        "## 사용 예시",
        artifact.usage_example.strip() if artifact.usage_example else "- none provided",
        "",
        "## Evidence와 claim mapping",
        _evidence_claim_mapping(artifact),
        "",
        "## 현재 task에 적용하는 next steps",
        _next_steps(job=job, artifact=artifact),
        "",
        "## 버전/변경 이력",
        _bullet_or_none(
            [
                f"version: {artifact.version}",
                f"created_from_job: {job.id}",
                "initial draft generated by skill acquisition completion",
            ]
        ),
        "",
        "## Acquisition context",
        f"- job_id: {job.id}",
        f"- agent: {job.agent_name}",
        f"- project: {job.project or 'default'}",
    ]
    if job.task_summary:
        lines.append(f"- task_summary: {job.task_summary}")
    return "\n".join(lines).strip() + "\n"


def _bullet_or_none(items: list[str]) -> str:
    if not items:
        return "- none provided"
    return "\n".join(f"- {item}" for item in items)


def _clean_items(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _validate_artifact(artifact: SkillAcquisitionArtifact) -> None:
    if not artifact.title.strip():
        raise LibrarianValidationError("Skill artifact title is required")
    if not artifact.purpose.strip():
        raise LibrarianValidationError("Skill artifact purpose is required")
    if not artifact.content.strip():
        raise LibrarianValidationError("Skill artifact procedure content is required")
    evidence = _all_evidence_handles(artifact)
    if (
        artifact.source_summary is not None
        and artifact.source_summary.strip()
        and not evidence
    ):
        raise LibrarianValidationError(
            "Skill artifact source summary requires claim-linked evidence"
        )
    if (
        evidence
        and not (
            artifact.source_summary is not None and artifact.source_summary.strip()
        )
        and not _all_supported_claims(artifact)
    ):
        raise LibrarianValidationError(
            "Skill artifact evidence requires a source summary claim mapping"
        )
    if artifact.evidence_items and not _structured_evidence_complete(artifact):
        raise LibrarianValidationError(
            "Skill artifact evidence items require claim-linked source metadata"
        )
    if artifact.evidence_urls and not (
        artifact.source_summary is not None and artifact.source_summary.strip()
    ):
        raise LibrarianValidationError(
            "Skill artifact evidence requires a source summary claim mapping"
        )
    if artifact.risk_level is RiskLevel.HIGH and len(_evidence_sources(evidence)) < 2:
        raise LibrarianValidationError(
            "High-risk skill artifacts require at least two independent evidence sources"
        )


def _evidence_sources(evidence: list[str]) -> set[str]:
    sources: set[str] = set()
    for item in evidence:
        parsed = urlparse(item)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            sources.add(parsed.netloc.casefold())
            continue
        sources.add(item.casefold())
    return sources


def _all_evidence_handles(artifact: SkillAcquisitionArtifact) -> list[str]:
    handles = _clean_items(artifact.evidence_urls)
    handles.extend(
        item.url_or_path.strip()
        for item in artifact.evidence_items
        if item.url_or_path.strip()
    )
    return handles


def _structured_evidence_complete(artifact: SkillAcquisitionArtifact) -> bool:
    for item in artifact.evidence_items:
        if not item.url_or_path.strip():
            return False
        if not _clean_items(item.supports_claims):
            return False
    return True


def _all_supported_claims(artifact: SkillAcquisitionArtifact) -> list[str]:
    claims: list[str] = []
    for item in artifact.evidence_items:
        claims.extend(_clean_items(item.supports_claims))
    return claims


def _verify_saved_contract(
    *,
    saved_body: str,
    saved_frontmatter: JSONObject,
    expected_body: str,
    expected_frontmatter: JSONObject,
) -> None:
    if saved_body.strip() != expected_body.strip():
        raise LibrarianValidationError("Published skill artifact body read-back failed")
    missing_sections = [
        section for section in _REQUIRED_SKILL_SECTIONS if section not in saved_body
    ]
    if missing_sections:
        raise LibrarianValidationError(
            "Published skill artifact missing required sections: "
            + ", ".join(missing_sections)
        )
    required_frontmatter = (
        "version",
        "purpose",
        "when_to_use",
        "when_not_to_use",
        "required_tools",
        "risk_level",
        "created_by",
        "source_job_id",
        "source_prompt_id",
        "evidence_urls",
        "evidence_items",
        "source_summary",
        "created_at",
        "reviewed_at",
        "supersedes",
    )
    missing_frontmatter = [
        key for key in required_frontmatter if key not in saved_frontmatter
    ]
    if missing_frontmatter:
        raise LibrarianValidationError(
            "Published skill artifact missing required frontmatter: "
            + ", ".join(missing_frontmatter)
        )
    for key in required_frontmatter:
        if saved_frontmatter[key] != expected_frontmatter[key]:
            raise LibrarianValidationError(
                f"Published skill artifact frontmatter mismatch: {key}"
            )


def _input_contract(artifact: SkillAcquisitionArtifact) -> str:
    items = _clean_items(artifact.required_tools)
    lines = ["- required_tools: " + (", ".join(items) if items else "none declared")]
    if artifact.input_schema:
        lines.extend(["- input_schema:", _json_block(artifact.input_schema)])
    else:
        lines.append("- input_schema: none provided")
    return "\n".join(lines)


def _output_contract(artifact: SkillAcquisitionArtifact) -> str:
    if artifact.output_schema:
        return "- output_schema:\n" + _json_block(artifact.output_schema)
    return _bullet_or_none(
        [
            "현재 task에 적용 가능한 절차, 산출물, 검증 또는 blocker를 명확히 반환한다.",
            "불확실하거나 실행 불가능한 조건은 limitations와 next steps에 남긴다.",
        ]
    )


def _evidence_claim_mapping(artifact: SkillAcquisitionArtifact) -> str:
    evidence_items = _evidence_item_payloads(artifact)
    if evidence_items:
        lines: list[str] = []
        for item in evidence_items:
            supports_claims = item.get("supports_claims")
            claims = (
                [claim for claim in supports_claims if isinstance(claim, str) and claim]
                if isinstance(supports_claims, list)
                else []
            )
            if not claims:
                claims = ["No claim mapping provided."]
            title = item.get("title")
            source_kind = item.get("source_kind")
            publisher = item.get("publisher_or_repository")
            freshness = item.get("freshness")
            lines.append(f"- {item['url_or_path']} supports: {', '.join(claims)}")
            if isinstance(title, str) and title:
                lines.append(f"  - title: {title}")
            if isinstance(source_kind, str) and source_kind:
                lines.append(f"  - source_kind: {source_kind}")
            if isinstance(publisher, str) and publisher:
                lines.append(f"  - publisher_or_repository: {publisher}")
            if isinstance(freshness, str) and freshness:
                lines.append(f"  - freshness: {freshness}")
        return "\n".join(lines)
    evidence = _clean_items(artifact.evidence_urls)
    source_summary = (artifact.source_summary or "No source summary provided.").strip()
    if not evidence:
        return _bullet_or_none(
            [
                "evidence: none provided",
                f"source_summary: {source_summary}",
                "external claims require reviewer verification before active promotion",
            ]
        )
    return "\n".join(f"- {url} supports: {source_summary}" for url in evidence)


def _next_steps(*, job: SkillAcquisitionJob, artifact: SkillAcquisitionArtifact) -> str:
    steps = _clean_items(artifact.next_steps)
    if steps:
        return _bullet_or_none(steps)
    if job.task_summary:
        return _bullet_or_none([f"Resume task: {job.task_summary}"])
    return "- Review this draft skill, then apply it only after prerequisites are met."


def _json_block(value: JSONValue) -> str:
    return "```json\n" + dumps_pretty_json(value).decode("utf-8") + "\n```"


def _handoff_payload(
    *,
    job: SkillAcquisitionJob,
    artifact: SkillAcquisitionArtifact,
    note_id: str,
    note_path: str,
) -> JSONObject:
    evidence = _evidence_item_payloads(artifact)
    job_payload: JSONObject = {
        "id": job.id,
        "status": "COMPLETED",
        "stage": SkillAcquisitionJobStage.HANDOFF_READY.value,
    }
    skill_payload: JSONObject = {
        "id": note_id,
        "title": artifact.title,
        "path": note_path,
        "status": "draft",
        "review_status": artifact.status.value,
        "version": artifact.version,
        "purpose": artifact.purpose,
        "application_summary": artifact.summary or artifact.purpose,
        "limitations": _skill_limitations(artifact),
    }
    persistence_payload: JSONObject = {
        "saved": True,
        "reindex_status": "succeeded",
        "verified": True,
        "verification_query": artifact.title,
    }
    current_task_payload: JSONObject = {
        "resume_summary": job.task_summary or job.prompt,
        "next_steps": _clean_items(artifact.next_steps),
        "stop_condition": (
            "Stop when the current task has applied the draft skill or when "
            "a prerequisite/tool/risk blocker is found."
        ),
    }
    warnings: list[JSONValue] = _handoff_warnings(artifact)
    payload: JSONObject = {
        "decision": "new_skill_acquired",
        "job": job_payload,
        "progress_summary": (
            "Draft skill artifact saved to Obsidian, refreshed through search, "
            "and verified by exact read-back before completion."
        ),
        "skill": skill_payload,
        "evidence": evidence,
        "persistence": persistence_payload,
        "current_task": current_task_payload,
        "warnings": warnings,
    }
    return payload


def _skill_limitations(artifact: SkillAcquisitionArtifact) -> list[JSONValue]:
    limitations: list[JSONValue] = [
        "draft skill; human review is required before active promotion"
    ]
    if artifact.status is ItemStatus.NEEDS_REVIEW:
        limitations.append("requested_status is needs_review; do not auto-apply")
    if not _all_evidence_handles(artifact):
        limitations.append("claim-linked evidence is missing or insufficient")
    return limitations


def _handoff_warnings(artifact: SkillAcquisitionArtifact) -> list[JSONValue]:
    warnings: list[JSONValue] = []
    if artifact.status is ItemStatus.NEEDS_REVIEW:
        warnings.append(
            {
                "code": "artifact_needs_review",
                "message": (
                    "Evidence or risk review is incomplete; keep the acquired "
                    "skill in needs_review before active use."
                ),
            }
        )
    if not _all_evidence_handles(artifact):
        warnings.append(
            {
                "code": "evidence_insufficient",
                "message": (
                    "No claim-linked evidence was provided; reviewer "
                    "verification is required before active promotion."
                ),
            }
        )
    return warnings


def _evidence_item_payloads(artifact: SkillAcquisitionArtifact) -> list[JSONObject]:
    structured = [
        _evidence_item_payload(item=item, default_title=artifact.title)
        for item in artifact.evidence_items
        if item.url_or_path.strip()
    ]
    if structured:
        return structured
    return [
        {
            "url_or_path": url,
            "title": artifact.title,
            "source_kind": "source",
            "publisher_or_repository": None,
            "accessed_at": None,
            "supports_claims": [artifact.source_summary or artifact.purpose],
            "freshness": None,
            "notes": None,
        }
        for url in _clean_items(artifact.evidence_urls)
    ]


def _evidence_item_payload(
    *,
    item: SkillAcquisitionEvidenceItem,
    default_title: str,
) -> JSONObject:
    return {
        "url_or_path": item.url_or_path.strip(),
        "title": _clean_optional(item.title) or default_title,
        "source_kind": _clean_optional(item.source_kind) or "source",
        "publisher_or_repository": _clean_optional(item.publisher_or_repository),
        "accessed_at": _clean_optional(item.accessed_at),
        "supports_claims": _clean_items(item.supports_claims),
        "freshness": _clean_optional(item.freshness),
        "notes": _clean_optional(item.notes),
    }


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
