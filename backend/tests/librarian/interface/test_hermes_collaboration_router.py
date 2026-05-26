"""Hermes librarian collaboration router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.delegate_execution import (
    LibrarianDelegateExecutor,
    LibrarianExecutionPlan,
)
from app.librarian.application.hermes_collaboration_service import (
    HermesCollaborationService,
)
from app.librarian.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
    LibrarianDelegateResult,
)
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.event_enum.collaboration_enums import (
    LibrarianDelegateStatus,
)
from app.librarian.domain.repositories.agent_repository import IAgentRepository
from app.main import app
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import MemoryCompactStatus
from app.memory.domain.repositories.memory_compact_repository import MemoryCompactCreate
from app.shared.types.extra_types import JSONObject
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider

FIXED_NOW = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)


class CollaborationProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for collaboration route tests."""

    def __init__(self, providers: list[LibrarianProvider]) -> None:
        """Store provider rows returned by list/get operations."""
        self.providers = providers

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is unused by collaboration route tests."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return one provider by id."""
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        return None

    async def list_all(self) -> list[LibrarianProvider]:
        """Return all stored providers."""
        return self.providers

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is unused by collaboration route tests."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is unused by collaboration route tests."""
        raise NotImplementedError


class CollaborationAgentRepository(IAgentRepository):
    """In-memory agent profile repository for collaboration route tests."""

    def __init__(self, profiles: list[AgentProfile]) -> None:
        """Store profile rows returned by get operations."""
        self.profiles = profiles

    async def create(self, payload: AgentCreate) -> AgentProfile:
        """Create is unused by collaboration route tests."""
        raise NotImplementedError

    async def get(self, agent_id: str) -> AgentProfile | None:
        """Return one agent profile by id."""
        for profile in self.profiles:
            if profile.id == agent_id:
                return profile
        return None

    async def list_all(self) -> list[AgentProfile]:
        """Return all stored agent profiles."""
        return self.profiles

    async def update(self, agent_id: str, payload: AgentUpdate) -> AgentProfile:
        """Update is unused by collaboration route tests."""
        raise NotImplementedError

    async def delete(self, agent_id: str) -> None:
        """Delete is unused by collaboration route tests."""
        raise NotImplementedError


class CollaborationSecretRepository(IProviderSecretRepository):
    """In-memory provider secret repository for collaboration route tests."""

    def __init__(self, secrets: dict[tuple[str, str], str] | None = None) -> None:
        """Store provider secrets by provider id and key name."""
        self.secrets = {} if secrets is None else secrets

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return one stored secret value."""
        return self.secrets.get((provider_id, key_name))

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Set secret is unused by collaboration route tests."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete secret is unused by collaboration route tests."""
        raise NotImplementedError


class SkippingDelegateExecutor(LibrarianDelegateExecutor):
    """Fake executor that simulates provider execution failure."""

    async def execute(
        self,
        *,
        command: HermesLibrarianAskCommand,
        plan: LibrarianExecutionPlan,
        fallback: LibrarianDelegateResult,
    ) -> LibrarianDelegateResult:
        """Return a skipped delegate without raising across the boundary.

        Args:
            command: Ask-librarian command under execution.
            plan: Resolved delegate execution plan.
            fallback: Deterministic delegate metadata.

        Returns:
            LibrarianDelegateResult: Skipped delegate failure evidence.
        """
        return LibrarianDelegateResult(
            profile_id=fallback.profile_id,
            provider_id=fallback.provider_id,
            status=LibrarianDelegateStatus.SKIPPED,
            delegate_type=fallback.delegate_type,
            summary=f"Provider execution failed for: {command.prompt}",
            matched_specialties=fallback.matched_specialties,
        )


class ActionDelegateExecutor(LibrarianDelegateExecutor):
    """Fake executor that returns a backend-action candidate."""

    async def execute(
        self,
        *,
        command: HermesLibrarianAskCommand,
        plan: LibrarianExecutionPlan,
        fallback: LibrarianDelegateResult,
    ) -> LibrarianDelegateResult:
        """Return a daily Memory Compact candidate from the librarian lane."""
        return LibrarianDelegateResult(
            profile_id=fallback.profile_id,
            provider_id=fallback.provider_id,
            status=LibrarianDelegateStatus.COMPLETED,
            delegate_type=fallback.delegate_type,
            summary=(
                "ACTION: DAILY_MEMORY_COMPACT\n\n"
                "# Daily Memory Compact\n\n"
                "## Summary\n"
                "The librarian compacted today's durable project memory."
            ),
            matched_specialties=fallback.matched_specialties,
        )


class RecordingMemoryCompactService(MemoryCompactService):
    """Record Memory Compact creation payloads without touching persistence."""

    def __init__(self) -> None:
        """Initialize the in-memory recording service."""
        self.payloads: list[MemoryCompactCreate] = []

    async def create(self, payload: MemoryCompactCreate) -> MemoryCompact:
        """Record the payload and return a compact read model."""
        self.payloads.append(payload)
        compact_id = f"compact-{len(self.payloads)}"
        return MemoryCompact(
            id=compact_id,
            project=payload.project,
            covered_from=payload.covered_from,
            covered_to=payload.covered_to,
            markdown_body=payload.markdown_body,
            status=payload.status,
            source_refs=tuple(
                MemoryCompactSourceRef(
                    id=f"ref-{index}",
                    compact_id=compact_id,
                    source_type=source_ref.source_type,
                    source_id=source_ref.source_id,
                    title=source_ref.title,
                    detail_path=source_ref.detail_path,
                )
                for index, source_ref in enumerate(payload.source_refs, start=1)
            ),
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
            archived_at=None,
        )


def _provider(
    provider_id: str = "00000000-0000-4000-8000-000000000701",
    *,
    enabled: bool = True,
    config: JSONObject | None = None,
) -> LibrarianProvider:
    """Build a provider read model for collaboration route tests."""
    return LibrarianProvider(
        id=provider_id,
        name="codex-oauth",
        provider_type=ProviderType.OPENAI_CODEX.value,
        auth_type=AuthType.OAUTH.value,
        enabled=enabled,
        config={} if config is None else config,
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )


def _profile(
    profile_id: str = "00000000-0000-4000-8000-000000000601",
    provider_id: str = "00000000-0000-4000-8000-000000000701",
    *,
    role: str = "DEFAULT_SEARCH",
    specialties: list[str] | None = None,
    routing_priority: int = 100,
) -> AgentProfile:
    """Build an agent profile read model for collaboration route tests."""
    return AgentProfile(
        id=profile_id,
        name="Hermes Librarian",
        provider=ProviderType.OPENAI_CODEX.value,
        description="Use project memory first.",
        capabilities=["library-search"],
        preferred_librarian_provider=provider_id,
        preferred_librarian_model="gpt-5.5",
        max_librarian_agents=2,
        librarian_role_prompt="Use project memory before web search.",
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
        librarian_role=role,
        librarian_specialties=specialties,
        librarian_routing_priority=routing_priority,
    )


def _service(
    providers: list[LibrarianProvider],
    profiles: list[AgentProfile] | None = None,
    secrets: dict[tuple[str, str], str] | None = None,
    delegate_executor: LibrarianDelegateExecutor | None = None,
    memory_compact_service: MemoryCompactService | None = None,
) -> HermesCollaborationService:
    """Create collaboration service with deterministic clock."""
    return HermesCollaborationService(
        provider_repo=CollaborationProviderRepository(providers),
        agent_repo=CollaborationAgentRepository([] if profiles is None else profiles),
        secret_repo=CollaborationSecretRepository(secrets),
        now_provider=lambda: FIXED_NOW,
        delegate_executor=delegate_executor,
        memory_compact_service=memory_compact_service,
    )


def _oauth_execution_secrets(
    provider_id: str = "00000000-0000-4000-8000-000000000701",
) -> dict[tuple[str, str], str]:
    """Return OAuth secret material that makes a provider executable."""
    return {
        (provider_id, ProviderSecretKey.OAUTH_ACCESS_TOKEN.value): "access-token",
        (
            provider_id,
            ProviderSecretKey.OAUTH_EXPIRES_AT.value,
        ): "2026-05-15T12:10:00+00:00",
    }


def test_ask_librarian_suggests_hermes_research_without_provider() -> None:
    """POST /librarians/ask should degrade to Hermes self-acquisition."""
    service = _service([])

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need an OAuth callback review skill",
                "agent_name": "Hermes",
                "project": "alexandria-hermes",
                "task_summary": "Review OAuth lifecycle",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["job_id"].startswith("librarian-job-")
    assert body | {"job_id": "stable"} == {
        "job_id": "stable",
        "status": "GUIDANCE_ONLY",
        "decision": "SUGGEST_HERMES_RESEARCH",
        "librarian_available": False,
        "self_acquisition_allowed": True,
        "recommendation": (
            "적절한 skill이 없다면 Hermes가 먼저 공식 문서나 웹 근거를 조사해 "
            "skill candidate를 제출할 수 있습니다. 바쁘면 사서에게 위임하세요."
        ),
        "provider_id": None,
        "candidate_id": None,
        "librarian_profile_id": None,
        "librarian_model": None,
        "librarian_role_prompt": None,
        "max_librarian_agents": None,
        "route_preview": [
            "Hermes direct search first",
            "No librarian profiles configured",
            "Routing reason: No librarian profiles configured",
            "No executable librarian provider available",
            "Hermes self-acquisition path",
        ],
        "selected_profiles": [],
        "matched_specialties": [],
        "quality_review_added": False,
        "routing_reason": "No librarian profiles configured",
        "delegates": [],
    }


def test_ask_librarian_delegates_when_provider_is_available() -> None:
    """POST /librarians/ask should create a lightweight delegated job."""
    profile = _profile()
    service = _service([_provider()], [profile], _oauth_execution_secrets())

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need an MCP usage-recording skill",
                "delegate_to_librarian": True,
                "librarian_profile_id": profile.id,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["job_id"].startswith("librarian-job-")
    assert body | {"job_id": "stable"} == {
        "job_id": "stable",
        "status": "COMPLETED",
        "decision": "DELEGATE_TO_LIBRARIAN",
        "librarian_available": True,
        "self_acquisition_allowed": True,
        "recommendation": (
            "사서 delegate가 완료되었습니다. delegates 응답에서 profile별 결과와 "
            "matched_specialties를 확인하세요."
        ),
        "provider_id": "00000000-0000-4000-8000-000000000701",
        "candidate_id": None,
        "librarian_profile_id": "00000000-0000-4000-8000-000000000601",
        "librarian_model": "gpt-5.5",
        "librarian_role_prompt": "Use project memory before web search.",
        "max_librarian_agents": 2,
        "route_preview": [
            "Hermes direct search first",
            "Selected profiles: 00000000-0000-4000-8000-000000000601",
            "Routing reason: Requested librarian profile 00000000-0000-4000-8000-000000000601",
            "Specialized librarian provider: 00000000-0000-4000-8000-000000000701",
            "Completed delegated librarians: 1",
        ],
        "selected_profiles": ["00000000-0000-4000-8000-000000000601"],
        "matched_specialties": [],
        "quality_review_added": False,
        "routing_reason": (
            "Requested librarian profile 00000000-0000-4000-8000-000000000601"
        ),
        "delegates": [
            {
                "profile_id": "00000000-0000-4000-8000-000000000601",
                "provider_id": "00000000-0000-4000-8000-000000000701",
                "status": "COMPLETED",
                "delegate_type": "LIBRARY_SEARCH",
                "summary": "Default search librarian checked reusable library/search routes.",
                "matched_specialties": [],
            }
        ],
    }


def test_ask_librarian_accepts_provider_and_profile_name_aliases() -> None:
    """POST /librarians/ask should resolve user-facing provider/profile names."""
    profile = _profile(profile_id="00000000-0000-4000-8000-000000000611")
    profile = AgentProfile(
        id=profile.id,
        name="research-critic",
        provider=profile.provider,
        description=profile.description,
        capabilities=profile.capabilities,
        preferred_librarian_provider=None,
        preferred_librarian_model=profile.preferred_librarian_model,
        max_librarian_agents=profile.max_librarian_agents,
        librarian_role_prompt=profile.librarian_role_prompt,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        librarian_role=profile.librarian_role,
        librarian_specialties=profile.librarian_specialties,
        librarian_routing_priority=profile.librarian_routing_priority,
    )
    service = _service([_provider()], [profile], _oauth_execution_secrets())

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need graph relation review before writing notes",
                "delegate_to_librarian": True,
                "provider_id": "codex-oauth",
                "librarian_profile_id": "research-critic",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "COMPLETED"
    assert {
        "provider_id": body["provider_id"],
        "librarian_profile_id": body["librarian_profile_id"],
        "selected_profiles": body["selected_profiles"],
        "routing_reason": body["routing_reason"],
    } == {
        "provider_id": "00000000-0000-4000-8000-000000000701",
        "librarian_profile_id": profile.id,
        "selected_profiles": [profile.id],
        "routing_reason": "Requested librarian profile research-critic",
    }
    assert body["delegates"] == [
        {
            "profile_id": profile.id,
            "provider_id": "00000000-0000-4000-8000-000000000701",
            "status": "COMPLETED",
            "delegate_type": "LIBRARY_SEARCH",
            "summary": "Default search librarian checked reusable library/search routes.",
            "matched_specialties": [],
        }
    ]


def test_ask_librarian_saves_daily_memory_compact_from_delegate_action() -> None:
    """POST /librarians/ask should persist delegate-approved compact actions."""
    profile = _profile()
    memory_service = RecordingMemoryCompactService()
    service = _service(
        [_provider()],
        [profile],
        _oauth_execution_secrets(),
        delegate_executor=ActionDelegateExecutor(),
        memory_compact_service=memory_service,
    )

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Please summarize today's long-term project memory.",
                "project": "alexandria-hermes",
                "delegate_to_librarian": True,
                "librarian_profile_id": profile.id,
                "source_refs": [
                    {
                        "source_type": "CONTEXT",
                        "source_id": "context-1",
                        "title": "Today's context",
                        "detail_path": "/memory/contexts/context-1",
                        "preview": "Relevant project memory.",
                    }
                ],
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert len(memory_service.payloads) == 1
    compact_payload = memory_service.payloads[0]
    assert compact_payload.project == "alexandria-hermes"
    assert compact_payload.covered_from == FIXED_NOW - timedelta(days=1)
    assert compact_payload.covered_to == FIXED_NOW
    assert compact_payload.status is MemoryCompactStatus.CURRENT
    assert compact_payload.markdown_body == (
        "# Daily Memory Compact\n\n"
        "## Summary\n"
        "The librarian compacted today's durable project memory."
    )
    assert [
        {
            "source_type": source_ref.source_type,
            "source_id": source_ref.source_id,
            "title": source_ref.title,
            "detail_path": source_ref.detail_path,
        }
        for source_ref in compact_payload.source_refs
    ] == [
        {
            "source_type": "CONTEXT",
            "source_id": "context-1",
            "title": "Today's context",
            "detail_path": "/memory/contexts/context-1",
        }
    ]
    assert body["status"] == "COMPLETED"
    assert body["route_preview"][-1] == "Saved daily Memory Compact: compact-1"
    assert body["delegates"][0]["summary"].startswith("# Memory Compact saved")
    assert "ACTION: DAILY_MEMORY_COMPACT" not in body["delegates"][0]["summary"]


def test_ask_librarian_reports_guidance_when_provider_delegate_is_skipped() -> None:
    """POST /librarians/ask should not mark skipped delegates as completed."""
    profile = _profile()
    service = _service(
        [_provider()],
        [profile],
        _oauth_execution_secrets(),
        delegate_executor=SkippingDelegateExecutor(),
    )

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need an MCP usage-recording skill",
                "delegate_to_librarian": True,
                "librarian_profile_id": profile.id,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "GUIDANCE_ONLY"
    assert body["decision"] == "SUGGEST_HERMES_RESEARCH"
    assert body["recommendation"] == (
        "사서 delegate를 완료하지 못했습니다. delegates 응답의 SKIPPED 항목과 "
        "summary를 확인하고 Hermes 직접 조사 또는 인증/제공자 설정을 점검하세요."
    )
    assert body["route_preview"][-1] == "No delegated librarians completed"
    assert body["delegates"] == [
        {
            "profile_id": profile.id,
            "provider_id": "00000000-0000-4000-8000-000000000701",
            "status": "SKIPPED",
            "delegate_type": "LIBRARY_SEARCH",
            "summary": "Provider execution failed for: Need an MCP usage-recording skill",
            "matched_specialties": [],
        }
    ]


def test_ask_librarian_routes_by_specialty_and_adds_quality_reviewer() -> None:
    """POST /librarians/ask should route matching specialties and risk review."""
    specialist = _profile(
        "00000000-0000-4000-8000-000000000602",
        role="SPECIALIST",
        specialties=["oauth", "fastapi"],
        routing_priority=10,
    )
    reviewer = _profile(
        "00000000-0000-4000-8000-000000000603",
        role="QUALITY_REVIEWER",
        specialties=["security"],
        routing_priority=15,
    )
    default = _profile(
        "00000000-0000-4000-8000-000000000604",
        role="DEFAULT_SEARCH",
        specialties=["library-search"],
        routing_priority=100,
    )
    service = _service(
        [_provider()],
        [default, specialist, reviewer],
        _oauth_execution_secrets(),
    )

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need an OAuth security review",
                "delegate_to_librarian": True,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "DELEGATE_TO_LIBRARIAN"
    assert body["selected_profiles"] == [specialist.id, reviewer.id]
    assert body["matched_specialties"] == ["oauth", "security"]
    assert body["quality_review_added"] is True
    assert body["routing_reason"] == (
        "Matched specialties and added quality reviewer for risk tokens"
    )
    assert [delegate["delegate_type"] for delegate in body["delegates"]] == [
        "SPECIALTY_REVIEW",
        "QUALITY_REVIEW",
    ]


def test_route_preview_returns_route_without_delegating() -> None:
    """POST /librarians/route-preview should show routing without queued delegation."""
    profile = _profile()
    service = _service([_provider()], [profile], _oauth_execution_secrets())

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/route-preview",
            json={
                "prompt": "Need an MCP usage-recording skill",
                "delegate_to_librarian": True,
                "librarian_profile_id": profile.id,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "SUGGEST_HERMES_RESEARCH"
    assert body["route_preview"] == [
        "Hermes direct search first",
        "Selected profiles: 00000000-0000-4000-8000-000000000601",
        "Routing reason: Requested librarian profile 00000000-0000-4000-8000-000000000601",
        "Specialized librarian provider: 00000000-0000-4000-8000-000000000701",
        "Preview only; no librarian delegation queued",
    ]


def test_ask_librarian_request_values_override_profile_defaults() -> None:
    """POST /librarians/ask should let Hermes override profile execution settings."""
    profile = _profile()
    service = _service([_provider()], [profile], _oauth_execution_secrets())

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need a deep review",
                "delegate_to_librarian": True,
                "librarian_profile_id": profile.id,
                "librarian_model": "gpt-5.4",
                "librarian_role_prompt": "Perform a narrow security review.",
                "max_librarian_agents": 1,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider_id"] == "00000000-0000-4000-8000-000000000701"
    assert body["librarian_profile_id"] == profile.id
    assert body["librarian_model"] == "gpt-5.4"
    assert body["librarian_role_prompt"] == "Perform a narrow security review."
    assert body["max_librarian_agents"] == 1


def test_ask_librarian_suggests_self_research_when_oauth_provider_lacks_token() -> None:
    """POST /librarians/ask should not delegate to providers without OAuth tokens."""
    profile = _profile()
    service = _service([_provider()], [profile])

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need a guarded OAuth review",
                "delegate_to_librarian": True,
                "librarian_profile_id": profile.id,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "SUGGEST_HERMES_RESEARCH"
    assert body["librarian_available"] is False
    assert body["provider_id"] is None
    assert body["librarian_profile_id"] == profile.id


def test_ask_librarian_rejects_missing_profile() -> None:
    """POST /librarians/ask should reject unknown librarian profile ids."""
    service = _service([_provider()])

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/ask",
            json={
                "prompt": "Need a deep review",
                "delegate_to_librarian": True,
                "librarian_profile_id": "missing-profile",
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Librarian profile not found: missing-profile"}


def test_librarian_job_status_returns_guidance_only_status() -> None:
    """GET /librarians/jobs/{job_id} should not overclaim durable completion."""
    service = _service([_provider()])

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/librarians/jobs/librarian-job-abc123")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "librarian-job-abc123",
        "status": "GUIDANCE_ONLY",
        "result_available": False,
        "message": (
            "No durable librarian job is queued; ask responses use "
            "synchronous delegates and return results inline."
        ),
    }


def test_librarian_job_status_rejects_unknown_job_shape() -> None:
    """GET /librarians/jobs/{job_id} should reject unsupported job ids."""
    service = _service([])

    with (
        override_library_provider("hermes_collaboration_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/librarians/jobs/not-a-job")

    assert response.status_code == 404
    assert response.json() == {"detail": "Librarian job not found: not-a-job"}
