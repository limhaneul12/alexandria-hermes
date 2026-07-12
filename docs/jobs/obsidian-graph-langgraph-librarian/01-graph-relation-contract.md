---
alexandria_type: job_plan
id: job_obsidian_graph_langgraph_librarian_01_graph_relation_contract
tags:
  - obsidian
  - graph
  - frontmatter
  - wikilink
status: implemented
created_at: "2026-05-26"
source: codex
---

# Graph Relation Contract

## 목표

Obsidian 기본 graph/backlink가 Alexandria 지식 관계를 자연스럽게 보여주도록 Markdown frontmatter와 본문 wikilink 규칙을 정의한다.

## 원칙

- Graph의 원본은 Markdown 파일이다.
- SQLite edge row는 재생성 가능한 cache다.
- 사람이 읽는 link는 본문 wikilink로 둔다.
- 기계가 읽는 안정 relation은 frontmatter에 둔다.
- 파일 이동에 강한 관계는 `id` 기반으로 보존하고, Obsidian UI용 관계는 `path`/wikilink로 렌더링한다.

## Relation 필드

공통 frontmatter 확장 후보:

```yaml
---
alexandria_type: context
id: ctx_example
tags:
  - alexandria
status: active
created_at: "2026-05-26T00:00:00Z"
source: obsidian-plugin
source_refs:
  - id: alexandria_start_here
    path: START_HERE.md
    relation: cites
derived_from:
  - id: librarian_chat_20260526_example
    path: _Ops/Librarian/Chats/librarian_chat_20260526_example.md
related:
  - id: skill_web_research
    path: Skills/Active/Web Research.md
supersedes: []
promotes_to: []
---
```

## Relation 종류

| relation | 의미 | 방향 |
| --- | --- | --- |
| `cites` | 답변/노트가 근거로 참조한 source | current -> source |
| `derived_from` | 사서 답변, research, context에서 파생 | current -> origin |
| `related` | 약한 관련성 | bidirectional candidate |
| `supersedes` | 이전 compact/note를 대체 | new -> old |
| `promotes_to` | chat/context가 skill/prompt 등으로 승격 | origin -> promoted |
| `blocks` | job/decision blocking relation | current -> blocker |
| `resolves` | bug/decision/job 해결 relation | current -> resolved |

## 본문 wikilink 섹션

사서 또는 backend가 note를 생성/갱신할 때 아래 섹션을 추가한다.

```md
## Alexandria Links

### Sources
- [[START_HERE]] — cites
- [[Jobs/Alexandria Obsidian Smoke Test]] — cites

### Related
- [[Skills/Active/Web Research]] — related

### Derived From
- [[_Ops/Librarian/Chats/librarian_chat_20260526_example]]
```

## 자동 생성 규칙

- `source_refs`가 있으면 `## Alexandria Links > Sources`를 생성한다.
- 사서 transcript에서 Context/Skill/Prompt를 만들면 `derived_from`을 넣는다.
- Memory Compact current를 새로 만들면 이전 current를 `supersedes`로 연결한다.
- `related`는 자동 추천하되, 영구 저장은 사용자 승인 후 수행한다.
- 기존 사용자가 쓴 `## Alexandria Links` 밖 본문은 수정하지 않는다.

## 충돌/보존 규칙

- frontmatter update는 body를 보존한다.
- 자동 생성 섹션은 marker를 둔다.

```md
<!-- ALEXANDRIA-LINKS:START -->
...
<!-- ALEXANDRIA-LINKS:END -->
```

- marker 밖 사용자 편집은 건드리지 않는다.
- path가 바뀌어도 `id`가 같으면 같은 note로 본다.

## 완료 기준

- 모든 새 note type이 relation frontmatter를 보존할 수 있다.
- source refs가 Obsidian wikilink로 렌더링된다.
- reindex가 frontmatter relation과 본문 wikilink를 모두 읽을 수 있다.
- path rename 후에도 id 기반 relation 복구가 가능하다.
