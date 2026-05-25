---
alexandria_type: job_plan
id: job_obsidian_alexandria_integration_03_sqlite_index_retrieval
tags:
  - sqlite
  - index
  - retrieval
  - rag
status: implemented
created_at: "2026-05-25"
source: codex
---

# SQLite Index and Retrieval Plan

## 결정

SQLite는 원본이 아니라 Obsidian Markdown을 빠르게 찾기 위한 재생성 가능한 검색/운영 캐시다.

## 역할

SQLite에 저장할 가치가 있는 것:

- vault file path, size, modified time, content hash.
- normalized frontmatter.
- `alexandria_type`, `id`, `title`, `tags`, `status`.
- Markdown chunk, heading path, excerpt.
- FTS index.
- embedding/vector index.
- access event, index run status, error log.
- librarian/skill-acquisition job state.
- provider/profile/OAuth 상태 같은 운영 메타데이터.

SQLite에 두면 안 되는 것:

- skill/prompt/context/body의 유일한 원본.
- Obsidian note와 다른 canonical copy.
- 사람이 수정할 수 없는 숨은 장기기억 원본.

## 테이블 후보

```text
obsidian_files
- vault_id
- relative_path
- content_hash
- size_bytes
- modified_at
- indexed_at
- alexandria_type
- note_id
- title
- frontmatter_json
- status
- index_status
- error_message

obsidian_chunks
- chunk_id
- vault_id
- note_id
- relative_path
- chunk_index
- heading_path
- text
- token_count
- content_hash

obsidian_embeddings
- chunk_id
- model
- dimensions
- vector
- embedded_at

index_runs
- run_id
- vault_id
- started_at
- finished_at
- status
- files_seen
- files_indexed
- errors_json

access_events
- event_id
- note_id
- relative_path
- query
- tool_name
- accessed_at
```

## reindex 흐름

```text
alexandria_reindex_vault
  -> vault root resolve
  -> .md 파일 scan
  -> frontmatter parse
  -> content hash 비교
  -> 변경 파일만 chunk 갱신
  -> FTS update
  -> embedding queue/update
  -> stale/deleted file mark
  -> index_run summary 기록
```

## retrieval 흐름

```text
query
  -> FTS/vector/hybrid search in SQLite
  -> candidate note ids/paths
  -> Obsidian Markdown 원문 재로드
  -> frontmatter 재검증
  -> excerpt/context pack 생성
  -> access event 기록
```

중요: 검색 결과를 만들 때 authoritative body는 가능하면 Markdown 파일에서 다시 읽는다.

## 검색 API 후보

```text
GET  /obsidian/index/status
POST /obsidian/index/rebuild
POST /obsidian/search
GET  /obsidian/notes/{note_id}
GET  /obsidian/notes/by-path?path=...
```

MCP tool 후보:

```text
alexandria_reindex_vault
alexandria_search_vault
alexandria_read_note
```

## 완료 기준

- temp vault fixture를 reindex할 수 있다.
- 변경 없는 두 번째 reindex가 중복 row를 만들지 않는다.
- 파일 삭제/이동이 stale 또는 deleted로 반영된다.
- FTS_ONLY 검색이 embedding 없이도 작동한다.
- HYBRID 검색은 vector가 unavailable일 때 graceful degradation한다.
