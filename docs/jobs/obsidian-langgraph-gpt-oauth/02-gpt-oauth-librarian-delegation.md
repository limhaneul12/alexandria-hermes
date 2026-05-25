---
alexandria_type: job_plan
id: job_obsidian_langgraph_gpt_oauth_02_gpt_oauth_librarian_delegation
tags:
  - oauth
  - gpt
  - librarian
  - delegation
status: implemented
created_at: "2026-05-26"
source: codex
---

# GPT OAuth Librarian Delegation

## 연결 방식

Obsidian workflow는 직접 token을 읽지 않는다. 승인된 `ask_oauth_librarian` action이 실행될 때만 backend의 기존 사서 협업 서비스를 호출한다.

```text
Obsidian workflow node
  -> HermesCollaborationService.ask_librarian
  -> profile routing
  -> provider execution policy
  -> OpenAIProviderDelegateExecutor
  -> OpenAI/Codex OAuth client config builder
```

## 입력

```json
{
  "delegate_to_librarian": true,
  "provider_id": "codex-oauth",
  "profile_id": "research-critic"
}
```

## 결과 병합

- delegate status는 workflow response의 `delegate_status`에 반영된다.
- delegate summaries는 답변 하단 `## GPT OAuth Librarian` 섹션에 붙는다.
- delegate raw payload는 workflow state의 `delegate_payload`에 저장된다.

## fallback

- profile/provider가 없으면 `GUIDANCE_ONLY`로 기록한다.
- 연결되지 않은 provider는 기존 협업 서비스가 local/self-acquisition route preview를 반환한다.
- OAuth token, refresh token, Authorization header는 Obsidian vault/plugin에 저장하지 않는다.
