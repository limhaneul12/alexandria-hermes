---
name: librarian-operator
description: Use when a task asks what Alexandria Librarian can do, how to use Librarian, or needs Librarian-backed Obsidian vault search, note-aware Q&A, vault curation, Memory Compact readiness, skill acquisition, or optional delegated librarian/provider guidance. Trigger on questions or actions involving Alexandria Librarian capabilities, librarian readiness, review queues, Obsidian side pane, skill acquisition, or search-first library operations.
---

# Librarian Operator

Use Alexandria Librarian as an optional Obsidian-aware library operator: search and cite existing knowledge first, then escalate to librarian/provider collaboration only when search is insufficient or the user explicitly asks.

## Operating rule

Follow this order unless the user explicitly asks for delegation:

1. Use current conversation, local files, loaded skills, and local memory.
2. Read the current Memory Compact for durable project context.
3. Search Context Vault/RAG and Obsidian notes.
4. Search reusable skill/prompt notes when the task is about capability reuse.
5. Ask the Obsidian-aware Librarian for synthesis over notes.
6. Delegate to a configured librarian/provider only as fallback or explicit escalation.

Never store secrets, OAuth tokens, pairing codes, or transient logs in notes.

## Capability map

### Search and recall existing library knowledge

Use this for “find prior decisions”, “what did we decide?”, “related notes”, or source-cited answers.

Preferred MCP tools:
- `alexandria_get_current_memory_compact(project=...)`
- `alexandria_search(query=..., project=..., include_scopes=...)`
- `alexandria_recall_context(query=..., project=...)`
- `alexandria_rag_context(query=..., project=...)`
- `alexandria_search_vault(query=..., project=..., alexandria_type=...)`
- `alexandria_read_note(note_id=... | path=...)`
- `alexandria_get_related_notes(note_id=... | path=...)`

Use project, workspace, agent, or session scope when known. Do not broaden a missing specific identity to global.

### Ask the Obsidian-aware Librarian

Use this for note-aware synthesis, active-note help, source-ref answers, extracting skill candidates, or deciding how to use material from the vault.

Tool:
- `alexandria_ask_obsidian_librarian`

Useful arguments:
- `query`: user question or requested librarian task.
- `active_note_path`: vault-relative path for the open note, if known.
- `selection`: selected Markdown, if supplied.
- `project`: usually the current repo/project.
- `preferred_alexandria_types`: e.g. `context`, `skill`, `prompt`, `memory_compact`, `job_plan`.
- `save_transcript`: false by default; true only when the user wants a durable chat note.
- `delegate_to_librarian`: false by default; true only for explicit escalation.

Example request shape:

```json
{
  "query": "이 노트에서 재사용 가능한 skill 후보를 뽑아줘",
  "active_note_path": "Contexts/Projects/alexandria-hermes/Some Note.md",
  "selection": "selected markdown if any",
  "project": "alexandria-hermes",
  "preferred_alexandria_types": ["context", "skill", "prompt", "memory_compact"],
  "save_transcript": false,
  "delegate_to_librarian": false
}
```

### Curate and reorganize the vault

Use this for “정리 필요한 노트”, “어디로 옮길지 계획”, “review queue”, or librarian curation.

Prefer non-mutating inspection first:

- `alexandria_librarian_readiness(project=...)`
- `alexandria_librarian_review_queue(project=..., scope_path=..., limit=...)`
- `alexandria_librarian_review_move_plan(project=..., scope_path=..., limit=...)`
- `alexandria_librarian_vault_inventory(project=...)`
- `alexandria_librarian_vault_path_search(query=...)`
- `alexandria_librarian_vault_move_plan(...)`

Only apply moves after an explicit plan is available and the user requested mutation:

- `alexandria_librarian_review_apply_moves(..., confirm_apply=true)`
- `alexandria_librarian_vault_apply_moves(..., confirm_apply=true)`

When using CLI directly, require `--confirm-apply` for non-empty move plans.

### Maintain Memory Compact and readiness

Use this for startup checks, “current memory stale?”, RAG/library health, or librarian readiness.

Tools/commands:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian check \
  --project alexandria-hermes \
  --refresh-compact \
  --summary
```

MCP equivalents:
- `alexandria_librarian_readiness(project=...)`
- `alexandria_librarian_refresh_current_compact(project=..., apply=...)`
- `alexandria_get_current_memory_compact(project=...)`
- `alexandria_review_memory_compact(compact_id=...)`

Treat `refresh-current-compact` as a planned mutation: inspect the plan first, apply only when refresh is required or explicitly forced.

### Skill acquisition and reusable capability capture

Use this when existing skills are missing or insufficient.

Search first:
- `alexandria_search_skills(capability=..., task_goal=..., project=...)`

Then, only if needed:
- `alexandria_librarian_brief_preview(prompt=..., project=...)`
- `alexandria_start_skill_acquisition(prompt=..., project=..., search_snapshot=...)`
- `alexandria_skill_acquisition_job_status(job_id=...)`
- `alexandria_complete_skill_acquisition(job_id=..., title=..., purpose=..., content=...)`

For guidance-only delegation:
- `alexandria_librarian_route_preview(prompt=..., project=...)`
- `alexandria_ask_librarian(prompt=..., delegate_to_librarian=false|true, project=...)`
- `alexandria_librarian_job_status(job_id=...)`

## Saving notes safely

Use `alexandria_save_note` for durable notes only when the output should become library knowledge.

Allowed note types commonly used:
- `context`
- `memory_compact`
- `skill`
- `prompt`
- `librarian_brief`
- `librarian_chat`
- `job_plan`

For updates to existing notes, prefer read-modify-write with content-hash conflict protection when the API exposes `expected_content_hash`. If a write conflict occurs, re-read, merge, and retry; do not blindly overwrite.

After saves or vault moves, run or request reindex:

- `alexandria_reindex_vault`
- Then verify search/readback for the saved or moved item.

## Response pattern

When explaining Librarian to a user, describe it as:

> Obsidian 기반 장기기억 도서관의 검색자, 정리자, 요약자, 스킬 후보 큐레이터, 그리고 필요 시 외부/전문 librarian provider로 escalation하는 운영 레이어.

Keep answers concrete:
- name the capability being used;
- list the MCP tool or CLI command;
- say whether the step is read-only or mutating;
- verify with readback, readiness, or search evidence before claiming completion.
