---
alexandria_type: job_plan
id: job_obsidian_alexandria_integration_04_mcp_cli_compatibility
tags:
  - mcp
  - cli
  - compatibility
  - agent
status: implemented
created_at: "2026-05-25"
source: codex
---

# Agent MCP/CLI Compatibility Plan

## 원칙

저장소를 Obsidian-first로 바꾸더라도 Hermes/Codex agent가 사용하는 MCP/CLI 경험은 최대한 유지한다.
기존 tool 이름은 wrapper로 유지하고 내부 구현만 Obsidian index 기반으로 교체한다.

## 기존 도구 매핑

| 기존 tool/command | 목표 동작 |
| --- | --- |
| `alexandria_search` | Obsidian index 전체 검색 |
| `alexandria_recall_context` | `alexandria_type=context` 중심 recall |
| `alexandria_rag_context` | explicit strategy 기반 Context Pack 생성 |
| `alexandria_get_current_memory_compact` | `memory_compact` 중 current compact 조회 |
| `alexandria_list_memory_compact_artifacts` | compact note 목록 조회 |
| `alexandria_search_library` | `skill`/`prompt` note 검색 |
| `alexandria_search_skills` | `alexandria_type=skill` 검색 |
| `alexandria_search_prompts` | `alexandria_type=prompt` 검색 |
| `alexandria_start_skill_acquisition` | skill 후보/job 생성 |
| `alexandria_complete_skill_acquisition` | skill Markdown note 생성 및 job 완료 |
| `alexandria_librarian_brief_preview` | Obsidian refs 기반 사서 knowledge packet preview |
| `alexandria_ask_librarian` | Obsidian-backed librarian ask |
| `alexandria_rag_status` | vault index/vector 상태 포함 |

## 새 도구 후보

새 도구는 내부 안정화와 Obsidian plugin 연동을 위해 추가한다.

```text
alexandria_reindex_vault
alexandria_search_vault
alexandria_read_note
alexandria_save_note
alexandria_update_frontmatter
alexandria_ask_obsidian_librarian
```

## 응답 shape 원칙

검색/조회 결과는 DB id보다 Obsidian id/path를 우선 반환한다.

```json
{
  "id": "skill_web_research",
  "alexandria_type": "skill",
  "path": "Alexandria/Skills/Active/Web Research.md",
  "title": "Web Research",
  "status": "active",
  "tags": ["research", "web-search"],
  "excerpt": "...",
  "source": "obsidian",
  "wikilink": "[[Alexandria/Skills/Active/Web Research]]"
}
```

## agent lookup 순서

```text
current conversation/local skill
  -> current Memory Compact
  -> targeted Context Vault recall
  -> skill/prompt note search
  -> self-acquisition
  -> optional librarian collaboration
```

사서 위임은 memory lookup의 필수 단계가 아니다.

## 완료 기준

- 기존 MCP tool smoke test가 Obsidian fixture를 대상으로 통과한다.
- 기존 CLI `context recall`, `memory-compacts current`, `librarian ask` 흐름이 깨지지 않는다.
- 응답에 `id`, `path`, `alexandria_type`, `wikilink`가 포함된다.
- deprecated DB-primary tool은 명확한 compatibility wrapper 또는 삭제 사유를 가진다.
