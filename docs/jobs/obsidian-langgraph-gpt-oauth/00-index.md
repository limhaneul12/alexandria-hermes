---
alexandria_type: job_plan
id: job_obsidian_langgraph_gpt_oauth_00_index
tags:
  - obsidian
  - langgraph
  - oauth
  - gpt-librarian
status: implemented
created_at: "2026-05-26"
source: codex
---

# Obsidian LangGraph + GPT OAuth Librarian — Index

## 목표

기존 Obsidian 사서 workflow를 “LangGraph-style” 수동 상태머신에서 실제 `langgraph` 패키지 기반 node executor로 전환한다.

```text
Obsidian Markdown = canonical knowledge
SQLite obsidian_* = search/edge/workflow cache
LangGraph SQLite checkpoint = pause/resume execution state
GPT OAuth librarian = optional approved delegate via backend provider store
```

## 결정

- `langgraph` / `langgraph-checkpoint-sqlite`를 backend 의존성으로 추가한다.
- workflow는 `StateGraph` node로 실행한다.
- human approval은 `interrupt(...)`와 `Command(resume=...)`로 처리한다.
- LangGraph checkpoint는 별도 SQLite 파일에 저장하고, 기존 `obsidian_librarian_workflows` row는 API 조회용 요약 checkpoint로 유지한다.
- GPT OAuth 사서 호출은 기존 `HermesCollaborationService` + OpenAI/Codex provider executor를 재사용한다.
- provider/profile이 없거나 연결되지 않으면 workflow를 실패시키지 않고 guidance-only/local fallback으로 남긴다.

## 작업 문서

| 문서 | 범위 |
| --- | --- |
| [01-langgraph-node-runtime.md](01-langgraph-node-runtime.md) | StateGraph node와 interrupt/resume runtime |
| [02-gpt-oauth-librarian-delegation.md](02-gpt-oauth-librarian-delegation.md) | GPT OAuth 사서 위임 연결 |
| [03-tests-rollout-and-ops.md](03-tests-rollout-and-ops.md) | 테스트, 운영, 완료 기준 |
