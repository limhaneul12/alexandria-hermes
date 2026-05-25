---
alexandria_type: job_plan
id: job_obsidian_alexandria_integration_09_tests_rollout_done
tags:
  - tests
  - rollout
  - done-criteria
  - verification
status: implemented
created_at: "2026-05-25"
source: codex
---

# Tests, Rollout, and Done Criteria

## rollout phases

### Phase 1 — read/index MVP

작업:

- `app/obsidian/*` 추가.
- frontmatter parser/writer.
- vault scanner.
- SQLite index schema/service.
- `reindex`, `search`, `read_note` API/MCP.

완료 기준:

- temp vault fixture scan 통과.
- 필수 frontmatter note 분류.
- path traversal 거부.
- unchanged reindex idempotent.

### Phase 2 — MCP/CLI read compatibility

작업:

- 기존 search/recall/read wrappers를 Obsidian index에 연결.
- skill/prompt/context/compact 검색 응답에 path/id/wikilink 추가.

완료 기준:

- 기존 MCP smoke test 유지.
- CLI context recall / memory compact current 동작.
- SQLite primary library CRUD 없이 read/search 가능.

### Phase 3 — write/capture

작업:

- context capture -> Markdown note.
- memory compact create/update -> Markdown note.
- skill acquisition complete -> skill draft note.
- prompt candidate -> prompt note.
- librarian chat transcript 저장.

완료 기준:

- 모든 생성 note에 필수 frontmatter.
- 저장 직후 검색 가능.
- body 보존 frontmatter update 테스트 통과.

### Phase 4 — librarian chat backend

작업:

- Obsidian context payload를 받는 ask endpoint.
- knowledge packet 구성.
- source refs/wikilink 반환.
- transcript save endpoint.

완료 기준:

- 현재 note/selection 기반 질문 가능.
- provider 없어도 self-answer fallback.
- transcript note가 `librarian_chat` frontmatter를 가진다.

### Phase 5 — Obsidian plugin MVP

작업:

- command palette command.
- right side pane chat view.
- active note/selection capture.
- answer/source link rendering.
- save chat button.

완료 기준:

- Obsidian에서 사서에게 질문 가능.
- source link 클릭으로 note 이동.
- backend unavailable 상태 표시.

### Phase 6 — DB-primary cleanup

작업:

- old DB-primary skill/prompt/context code 제거 또는 wrapper 정리.
- migration/docs 업데이트.
- CI 안정화.

완료 기준:

- Obsidian Markdown이 유일한 canonical knowledge source.
- SQLite 삭제 후 reindex로 검색 복구.
- backend validation suite 통과.

## test matrix

| 영역 | 테스트 |
| --- | --- |
| frontmatter | parse, missing required, id collision, body-preserving update |
| vault path | path traversal, absolute path reject, safe relative path |
| index | initial scan, incremental scan, stale/deleted file handling |
| retrieval | FTS_ONLY, HYBRID fallback, source refs, original Markdown reload |
| write | context, compact, skill, prompt, librarian_chat note creation |
| security | secret pattern block/redaction, operator key protected routes |
| MCP/CLI | existing tool wrapper smoke, new Obsidian tools smoke |
| plugin | active note path, selection payload, answer render, save chat |

## required validation commands

Backend 변경 시 최소:

```bash
cd backend
uv run ruff check .
uv run pyrefly check
uv run pytest -q
```

문서만 변경한 경우:

```bash
find docs/jobs/obsidian-alexandria-integration -type f -name '*.md' -print | sort
```

## final done definition

완료라고 말하려면 아래가 모두 참이어야 한다.

- Obsidian vault가 원본 저장소로 동작한다.
- SQLite는 삭제/재생성 가능한 index/cache다.
- 기존 agent MCP/CLI read flow가 깨지지 않는다.
- write/capture 결과가 사람이 읽을 수 있는 Markdown이다.
- 사서 채팅창에서 현재 노트 기반 질의가 가능하다.
- 답변 source가 wikilink로 연결된다.
- 보안/충돌/동기화 위험이 테스트와 문서로 다뤄진다.
