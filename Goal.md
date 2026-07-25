# Goal — Memory Reconciliation Engine and Long-Term Memory Architecture Refactor

## Goal

Alexandria-Hermes를 기억을 저장하고 검색하는 시스템에서, 새로운 기억과 기존 기억의 관계를 판정하고 현재·과거의 유효 상태를 일관되게 유지하는 장기기억 관리 시스템으로 확장한다.

이번 작업은 Memory Reconciliation Engine의 완전한 구현과 해당 Touch-path의 구조 리팩토링을 하나의 목표로 수행한다. 구현은 `backend/.agents/docs/rule/규칙.md`, `backend/.agents/docs/rule/README.md`, 관련 세부 규칙을 Source of Truth로 따른다. Obsidian Markdown은 Canonical Storage이며 SQLite, FTS, Vector, Embedding, Graph는 재구축 가능한 Read Model 또는 Index다. 기존 미커밋 변경과 Public API, Import, Monkeypatch Seam, Recovery/Readiness 계약을 보존하고 사용자 요청 없이 Commit/Push하지 않는다.

## Required Relations

- `DUPLICATE`: 동일 Claim. 신규 Context를 만들지 않고 Evidence·Provenance만 멱등 병합한다.
- `SUPPORTS`: 독립 Evidence로 기존 Claim을 지지한다.
- `EXTENDS`: 기존 Claim에 조건·범위·원인·결과·세부사항을 추가한다.
- `CONTRADICTS`: 동일 Scope와 유효 기간에서 동시에 참일 수 없다. 양쪽을 보존하고 Conflict Set을 만든다.
- `SUPERSEDES`: 더 최신인 상태가 기존 현재 상태를 대체한다. 기존 기억은 삭제하지 않는다.
- `UNRELATED`: 비교 후보와 관계없는 신규 기억이다.
- `UNKNOWN`: Evidence·Scope·시간 정보가 부족해 신뢰할 수 있는 판정이 불가능하다.

## Design Principles

- Preserve, Do Not Erase. Reconciliation 정상 경로에서 Hard Delete하지 않는다.
- LLM Proposes, Policy Decides. 모델 출력은 제안이며 상태 변경은 명시적 정책이 결정한다.
- Deterministic Rules First. ID, Source Identity, Content Hash, Canonical Claim, 명시적 Supersede, 시간 범위, 기존 Graph Relation을 먼저 사용한다.
- Contradiction Is a First-Class State. 충돌을 숨기거나 임의로 하나의 사실로 합치지 않는다.
- Temporal Truth. `recorded_at`, `observed_at`, `valid_from`, `valid_to`를 구분한다.
- Idempotency. 반복 실행이 Context, Relation, Conflict, Evidence를 중복 생성하지 않는다.

## Domain Outcomes

다음을 구현한다.

- Memory Candidate와 Canonical Claim
- 관계별 다축 분류: semantic similarity, claim overlap, scope compatibility, temporal compatibility, source independence, polarity conflict, specificity change, freshness
- Preview 가능한 Reconciliation Plan
- 멱등적인 Apply와 Read-back Verification
- Reconciliation Result와 실패 코드
- Memory Conflict Set과 명시적 Resolution
- Temporal Context State와 Current/Historical Query
- Graph 관계 `duplicates`, `supports`, `extends`, `contradicts`, `supersedes`
- Reconciliation-aware Retrieval과 Memory Compact
- Obsidian Frontmatter의 Temporal·Conflict·Relation 메타데이터
- FastAPI API와 MCP Tool
- Dry-run/Apply Backfill
- Operational Readiness와 구조화된 실행 관측 정보

## Processing Pipeline

```text
Memory Candidate
→ Normalize and extract Canonical Claims
→ Exact identity/idempotency checks
→ Candidate recall by hash/source/claim/scope/FTS/vector/graph/history
→ Deterministic classification
→ Semantic classification
→ Optional LLM proposal
→ Decision aggregation
→ Reconciliation Plan
→ Policy validation
→ Atomic apply where possible
→ Canonical Context/Graph/Lifecycle/Evidence/Conflict updates
→ Read-back verification
→ Retrieval and Memory Compact refresh
```

## Lifecycle and Conflict

Lifecycle와 Temporal Validity는 별개다. 필요한 의미는 `DRAFT`, `ACTIVE`, `REVIEW_REQUIRED`, `CONFLICTED`, `SUPERSEDED`, `ARCHIVED`다. `SUPERSEDED`는 과거에 거짓이었다는 의미가 아니며, `CONFLICTED`는 삭제 대상이라는 의미가 아니다.

Conflict 상태는 최소한 `OPEN`, `REVIEWING`, `RESOLVED_KEEP_BOTH`, `RESOLVED_SUPERSEDED`, `RESOLVED_MERGED`, `RESOLVED_INVALID_SOURCE`를 지원한다.

## Public Use Cases

- `preview_memory_reconciliation`
- `apply_memory_reconciliation`
- `get_memory_reconciliation`
- `list_memory_conflicts`
- `resolve_memory_conflict`
- `reconcile_existing_memory`
- Temporal/Canonical Claim Backfill dry-run and apply

## Refactor Boundary

기존 `ContextService`에 모든 책임을 추가하지 않는다. Candidate, Recall, Classification, Temporal Policy, Plan, Apply, Conflict, Evidence Merge를 실제 책임 기준으로 분리한다. Router는 Boundary만 담당하고, Domain은 FastAPI·SQLAlchemy·Pydantic API Schema·Obsidian Adapter에 의존하지 않는다. 기존 Facade가 Public Contract라면 얇게 유지하고 새 구현을 위임 또는 재수출한다.

## Memory Compact Safety

Open Conflict, 동일 시간 범위의 모순, 현재/과거 혼재, Unknown/Review Required, Evidence 없는 Claim을 하나의 확정 사실로 압축하지 않는다. Compact는 current facts, historical facts, open conflicts, uncertain claims, superseded facts를 구분하고 다음 결함을 검출한다.

- unresolved contradiction leakage
- temporal state collapse
- superseded fact presented as current
- unsupported merge
- duplicate claim inflation

## Compatibility and Migration

기존 Context/RAG/Memory Compact/Graph/Obsidian/MCP API와 Markdown Round-trip을 보존한다. 기존 Context를 삭제하거나 전체 재작성하지 않는다. Temporal·Canonical Claim·Supersede·Duplicate·Conflict Backfill은 Dry-run을 제공하며 추론할 수 없는 `valid_from`을 임의 생성하지 않는다.

## Verification

각 안정 단위마다 관련 Unit/Integration/Repository/Router/Obsidian/Compact/MCP 테스트를 수행한다. 최종적으로 다음 품질 게이트를 통과해야 한다.

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run pyrefly check
uv run pytest -q
```

저장소의 Broad Type Guard와 Lazy Import Guard도 통과해야 하며 자동화된 Hard Violation은 0이어야 한다.

## Definition of Done

7개 관계 판정, Preview/Apply, 멱등성, Evidence 병합, Temporal Supersession, Conflict 보존·해결, Current/Historical Recall, Reconciliation-aware Compact, Obsidian Round-trip, Graph 관계, API/MCP, Migration/Backfill, Readiness/Observability가 구현되고 전체 품질 게이트가 통과해야 한다. Hard Delete는 수행되지 않고 기존 미커밋 변경은 손실되지 않으며 Commit/Push는 사용자 요청 전까지 수행하지 않는다.
