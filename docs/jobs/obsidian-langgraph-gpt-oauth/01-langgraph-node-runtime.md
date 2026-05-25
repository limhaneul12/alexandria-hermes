---
alexandria_type: job_plan
id: job_obsidian_langgraph_gpt_oauth_01_langgraph_node_runtime
tags:
  - langgraph
  - workflow
  - checkpoint
  - human-in-the-loop
status: implemented
created_at: "2026-05-26"
source: codex
---

# LangGraph Node Runtime

## Runtime graph

```text
START
  -> collect_context
  -> plan_actions
  -> approval_gate       # interrupt(...)
  -> execute_approved_actions
  -> finalize
  -> END
```

## Persistence

- LangGraph checkpoint path: `SERVICE_OBSIDIAN_LIBRARIAN_LANGGRAPH_CHECKPOINT_PATH`
- Default: `./data/obsidian_librarian_langgraph.sqlite`
- API-facing workflow row remains in `obsidian_librarian_workflows`.

## Approval contract

The approval node interrupts with:

```json
{
  "thread_id": "librarian_chat_...",
  "pending_actions": [
    {"id": "save_transcript"},
    {"id": "ask_oauth_librarian"}
  ],
  "approval_contract": "Command(resume={'approved_actions': [...]})"
}
```

Resume uses:

```python
Command(resume={"approved_actions": ["save_transcript"]})
```

## Safety

- Unknown actions are rejected before graph resume to avoid corrupting the checkpoint.
- Cancelled/completed workflows cannot be resumed.
- Cancel also deletes LangGraph checkpoints for the thread.
- Obsidian notes are written only in the post-approval execution node.
