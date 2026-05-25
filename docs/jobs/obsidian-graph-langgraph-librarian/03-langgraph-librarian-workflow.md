---
alexandria_type: job_plan
id: job_obsidian_graph_langgraph_librarian_03_langgraph_librarian_workflow
tags:
  - langgraph
  - librarian
  - workflow
  - human-in-the-loop
status: implemented
created_at: "2026-05-26"
source: codex
---

# LangGraph Librarian Workflow

## 목표

사서 ask를 단일 함수가 아니라 재개 가능한 workflow로 만든다.
LangGraph는 사서의 판단/위임/승인/저장 흐름을 관리한다.

## 역할 분리

```text
Obsidian = permanent knowledge
SQLite = search/index/cache
LangGraph checkpoint = workflow execution state
OAuth provider = optional external delegate
```

LangGraph checkpoint에는 장기기억 원문을 저장하지 않는다.
저장할 수 있는 것은 workflow state, step result 요약, pending action id, source note id/path 정도다.

## MVP State

```python
class LibrarianGraphState(TypedDict):
    query: str
    active_note_path: str | None
    selection: str | None
    project: str | None
    source_refs: list[SourceRef]
    related_refs: list[SourceRef]
    local_answer: str | None
    delegate_requested: bool
    delegate_result: str | None
    action_preview: list[ActionPreview]
    approval_required: bool
    approved_actions: list[str]
    transcript_path: str | None
```

## Node 설계

```text
collect_context
  -> read active note
  -> search related notes
  -> load current memory compact

classify_request
  -> answerable locally?
  -> needs graph action?
  -> needs OAuth delegation?

local_answer
  -> deterministic source-grounded answer

maybe_delegate
  -> if user requested or confidence low
  -> call OAuth provider route

propose_actions
  -> save chat?
  -> create context?
  -> create skill draft?
  -> add graph links?

interrupt_for_approval
  -> if action writes notes or calls external delegate without prior consent

apply_actions
  -> write markdown
  -> update graph links
  -> reindex

final_response
  -> answer + source refs + pending/completed actions
```

## Human-in-the-loop

중단이 필요한 경우:

- 외부 OAuth provider 호출 전, 사용자가 `delegate_to_librarian`을 켜지 않은 경우.
- note body/frontmatter를 수정하는 경우.
- transcript 자동 저장이 꺼져 있는데 저장을 제안하는 경우.
- relation을 자동으로 영구 저장하는 경우.

Obsidian plugin UX:

```text
사서 답변

Proposed actions:
[ ] Save transcript
[ ] Add links to current note
[ ] Create context note
[ ] Create skill draft
[ ] Ask OAuth librarian

[Apply selected]
```

## Persistence

초기 MVP는 local SQLite checkpointer를 사용한다.
LangGraph Platform은 도입하지 않는다.

저장 단위:

```text
thread_id = librarian_chat_<timestamp>_<hash>
checkpoint namespace = obsidian_librarian
```

## Backend endpoint 후보

```text
POST /obsidian/librarian/workflows
GET  /obsidian/librarian/workflows/{thread_id}
POST /obsidian/librarian/workflows/{thread_id}/resume
POST /obsidian/librarian/workflows/{thread_id}/cancel
```

기존 `/obsidian/librarian/ask`는 MVP 동안 synchronous wrapper로 유지한다.

## 완료 기준

- local answer workflow가 LangGraph로 실행된다.
- interrupt/resume으로 사용자 승인 후 note 저장이 가능하다.
- workflow checkpoint를 삭제해도 Obsidian 원본 note는 손상되지 않는다.
- 기존 `/obsidian/librarian/ask` API 응답 shape가 유지된다.
