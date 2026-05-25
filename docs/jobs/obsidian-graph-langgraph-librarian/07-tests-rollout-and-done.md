---
alexandria_type: job_plan
id: job_obsidian_graph_langgraph_librarian_07_tests_rollout_done
tags:
  - tests
  - rollout
  - verification
  - done-criteria
status: implemented
created_at: "2026-05-26"
source: codex
---

# Tests, Rollout, and Done Criteria

## Rollout phases

### Phase 1 — install hardening

작업:

- setup migration 자동화.
- launchd plist 안정화.
- plugin copy/symlink install mode.
- install smoke test command.

완료 기준:

- fresh SQLite DB에서 `/obsidian/init` 500이 없다.
- launchd backend가 재부팅 후 살아난다.
- plugin install이 Obsidian에서 인식된다.

### Phase 2 — graph relation contract

작업:

- relation frontmatter parse/render.
- generated `## Alexandria Links` marker section.
- source refs -> wikilink rendering.

완료 기준:

- body-preserving frontmatter update test 통과.
- marker section만 갱신하고 사용자 본문은 보존한다.
- generated note가 Obsidian graph에서 link로 보인다.

### Phase 3 — edge index

작업:

- `obsidian_edges` migration.
- reindex edge rebuild.
- related notes API/CLI/MCP.

완료 기준:

- SQLite 삭제 후 reindex로 edge 복구.
- current note related retrieval 통과.
- frontmatter relation과 body wikilink 모두 edge로 잡힌다.

### Phase 4 — plugin graph UI

작업:

- related notes panel.
- graph action preview/apply.
- OAuth delegate controls.

완료 기준:

- active note 기준 related notes 표시.
- apply selected actions 후 note/frontmatter/wikilink 변경 확인.
- backend unavailable 에러가 UI에 표시된다.

### Phase 5 — LangGraph workflow MVP

작업:

- local answer graph.
- action proposal.
- interrupt/resume approval.
- existing `/obsidian/librarian/ask` compatibility wrapper.

완료 기준:

- workflow checkpoint 생성/조회/재개 가능.
- 사용자 승인 전 write action 미실행.
- 기존 ask 응답 shape 유지.

### Phase 6 — OAuth delegated librarian

작업:

- provider/profile list in plugin.
- delegate node.
- token refresh error handling.
- local fallback.

완료 기준:

- OAuth token이 Obsidian vault/plugin data에 남지 않는다.
- provider disconnected/timeout/error가 local answer로 fallback된다.
- delegate result가 source_refs와 함께 표시된다.

## 테스트 목록

Backend:

```bash
cd backend
make ci
```

추가 테스트:

```text
tests/obsidian/test_graph_relations.py
tests/obsidian/test_obsidian_edges.py
tests/obsidian/test_related_notes.py
tests/obsidian/test_librarian_workflow.py
tests/cli/test_obsidian_install_local.py
```

Plugin:

```bash
node --check integrations/obsidian/alexandria-librarian/main.js
node -e "JSON.parse(require('fs').readFileSync('integrations/obsidian/alexandria-librarian/manifest.json','utf8'))"
```

Manual smoke:

```text
1. Obsidian open Alexandria vault.
2. Cmd+P → Ask Alexandria Librarian.
3. Ask active note question.
4. Related notes appear.
5. Apply source link action.
6. Obsidian graph shows new link.
7. Reindex keeps relation.
```

## 보안 검증

- Obsidian vault 내 token 문자열 scan.
- plugin `data.json` 내 OAuth credential 없음 확인.
- backend logs에 token 원문 없음 확인.
- external delegate result 저장은 사용자 승인 필요.

## Done criteria

- install-local 한 번으로 backend/vault/plugin/daemon 준비.
- Obsidian pane에서 current note 기반 사서 대화 가능.
- source/related link가 Obsidian graph에 반영.
- related notes API가 edge cache 기반으로 동작.
- LangGraph workflow가 local answer + approval resume을 지원.
- OAuth provider 위임이 plugin에서 선택적으로 가능.
- 모든 검증 명령 통과.

## 2026-05-26 G003 verification additions

Additional coverage added:

- LangGraph package runtime pauses and resumes through SQLite checkpoint persistence.
- Workflow resumes after service recreation using the same thread id.
- Approved GPT OAuth delegate action calls the delegate service and appends returned summary.
- Missing GPT profile falls back to `GUIDANCE_ONLY` instead of failing the workflow.
- Unknown actions are rejected before graph resume to protect checkpoint integrity.
